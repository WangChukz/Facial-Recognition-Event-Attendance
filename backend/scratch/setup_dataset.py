import os
import sys
import shutil
import re

# Tu dong reconfigure encoding de tranh loi Unicode tre Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

SRC_DIR = "c:/AI_event/AI_Project_2526/realdataset/real"
DST_DIR = "c:/AI_event/dataset_students"

# Bang anh xa thu cong cho cac truong hop dac biet
SPECIAL_MAPPING = {
    "Downloads - Đức Anh Nguyễn": "NguyenDucAnh",
    "NguyenDucAnh_real - Đức Anh Nguyễn": "NguyenDucAnh",
    "NguyenDucAnh_real - Đức Anh Nguyễn(1)": "NguyenDucAnh",
    "NguyenQuynhAnh_enroll - Trieu Duc Duy MIS01": "NguyenQuynhAnh",
    "TrieuDucDuy_enroll - Duyy Đức": "TrieuDucDuy",
}

def clean_name(folder_name):
    if folder_name in SPECIAL_MAPPING:
        return SPECIAL_MAPPING[folder_name]
        
    name_part = folder_name.split(" -")[0].strip()
    name_part = re.sub(r'_(real|enroll)$', '', name_part)
    return name_part

def check_image_type(file_path):
    """Doc magic bytes dau file de xac dinh loai anh thuc su."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(12)
        if len(header) < 4:
            return None
        
        # Check JPEG
        if header.startswith(b"\xff\xd8"):
            return "jpeg"
        # Check PNG
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        # Check HEIC
        if len(header) >= 12 and (b"ftypheic" in header or b"ftypmif1" in header or b"ftypmsf1" in header or b"ftypheix" in header):
            return "heic"
    except Exception:
        pass
    return None

def convert_heic_to_jpg(src_path, dst_path):
    """Chuyen doi anh HEIC cua iPhone sang JPEG."""
    try:
        from pillow_heif import register_heif_opener
        from PIL import Image
        register_heif_opener()
        image = Image.open(src_path)
        image.save(dst_path, "JPEG")
        return True
    except Exception as e:
        print(f"Warning: Failed to convert HEIC file '{src_path}' due to: {e}")
        return False

def setup_dataset():
    if not os.path.exists(SRC_DIR):
        print(f"Error: Source directory does not exist at: {SRC_DIR}")
        return

    os.makedirs(DST_DIR, exist_ok=True)
    print(f"Organizing dataset from '{SRC_DIR}' to '{DST_DIR}'...\n")

    student_folders = [f for f in os.listdir(SRC_DIR) if os.path.isdir(os.path.join(SRC_DIR, f))]
    
    summary = {}

    for folder in student_folders:
        src_folder_path = os.path.join(SRC_DIR, folder)
        cleaned_student_name = clean_name(folder)
        
        dst_student_path = os.path.join(DST_DIR, cleaned_student_name)
        os.makedirs(dst_student_path, exist_ok=True)
        
        valid_extensions = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
        copied_count = 0
        
        for root, dirs, files in os.walk(src_folder_path):
            for file in files:
                src_file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                
                is_image = False
                img_type = None
                
                if ext in valid_extensions:
                    is_image = True
                    img_type = ext[1:]
                elif ext == ".heic":
                    is_image = True
                    img_type = "heic"
                else:
                    # Neu file khong co duoi mo rong, check magic bytes
                    img_type = check_image_type(src_file_path)
                    if img_type in ("jpeg", "png", "heic"):
                        is_image = True
                
                if not is_image:
                    continue
                
                # Dat ten file moi theo dinh dang chuan
                new_file_name = f"{cleaned_student_name}_{copied_count:03d}"
                
                if img_type == "heic":
                    dst_file_path = os.path.join(dst_student_path, f"{new_file_name}.jpg")
                    # Chuyen doi HEIC -> JPG
                    success = convert_heic_to_jpg(src_file_path, dst_file_path)
                    if success:
                        copied_count += 1
                else:
                    # Copy va gan duoi tuong ung
                    target_ext = ".jpg" if img_type == "jpeg" else f".{img_type}"
                    dst_file_path = os.path.join(dst_student_path, f"{new_file_name}{target_ext}")
                    shutil.copy2(src_file_path, dst_file_path)
                    copied_count += 1
                    
        summary[cleaned_student_name] = summary.get(cleaned_student_name, 0) + copied_count

    print("================== DATASET ORGANIZATION REPORT ==================")
    total_images = 0
    for idx, (student, count) in enumerate(sorted(summary.items())):
        print(f"{idx+1:02d}. Student: {student:<25} | Images: {count}")
        total_images += count
    print("-----------------------------------------------------------------")
    print(f"Total students after grouping: {len(summary)}")
    print(f"Total copied images: {total_images}")
    print(f"New dataset directory: {DST_DIR}")
    print("=================================================================")

if __name__ == "__main__":
    setup_dataset()
