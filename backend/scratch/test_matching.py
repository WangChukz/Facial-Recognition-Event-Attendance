import pandas as pd
import os
import sys
import unicodedata
import re

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def remove_vietnamese_diacritics(text):
    if not isinstance(text, str):
        return ""
    # Chuyển unicode dựng sẵn về tổ hợp để dễ xử lý loại bỏ dấu
    text = unicodedata.normalize('NFD', text)
    # Loại bỏ các ký tự dấu tiếng Việt
    text = re.sub(r'[\u0300-\u036f]', '', text)
    # Thay thế chữ đ/Đ
    text = text.replace('đ', 'd').replace('Đ', 'D')
    # Chuyển về dạng chuẩn NFC
    text = unicodedata.normalize('NFC', text)
    # Loại bỏ khoảng trắng để có dạng viết liền
    text = text.replace(' ', '')
    return text

meta_path = "c:/AI_event/dataset/dataset/metadata.xlsx"
real_dir = "c:/AI_event/dataset/dataset/real"

if os.path.exists(meta_path) and os.path.exists(real_dir):
    df = pd.read_excel(meta_path)
    
    # Danh sách các thư mục con trong real/
    folders = sorted([d for d in os.listdir(real_dir) if os.path.isdir(os.path.join(real_dir, d))])
    
    # Rút gọn tên folder (ví dụ: 'BuiDucThinh_real' -> 'BuiDucThinh')
    folder_names = {}
    for f in folders:
        clean_name = f.replace('_real', '')
        folder_names[clean_name] = f
        
    print(f"Tổng số folder sinh viên: {len(folders)}")
    print(f"Tổng số sinh viên trong metadata: {len(df)}")
    
    matches = 0
    mapping_results = []
    
    for idx, row in df.iterrows():
        name_with_diacritics = row['Họ và tên']
        student_id = row['Mã sinh viên']
        student_class = row['Lớp']
        
        name_no_diacritics = remove_vietnamese_diacritics(name_with_diacritics)
        
        # Tìm xem name_no_diacritics có trong folder_names không
        matched_folder = None
        # So khớp case-insensitive
        for clean_f in folder_names:
            if clean_f.lower() == name_no_diacritics.lower():
                matched_folder = folder_names[clean_f]
                break
                
        if matched_folder:
            matches += 1
            mapping_results.append({
                "STT": row['STT'],
                "Mã sinh viên": student_id,
                "Họ và tên": name_with_diacritics,
                "Lớp": student_class,
                "Folder": matched_folder,
                "MatchKey": name_no_diacritics
            })
        else:
            print(f"KHÔNG KHỚP: {name_with_diacritics} -> {name_no_diacritics} (ID: {student_id})")
            
    print(f"\nKhớp thành công: {matches}/{len(df)} sinh viên.")
    
    if matches == len(df):
        print("-> TẤT CẢ SINH VIÊN ĐÃ ĐƯỢC ÁNH XẠ THÀNH CÔNG 100%!")
        print("\nVí dụ 5 bản ghi khớp đầu tiên:")
        for item in mapping_results[:5]:
            print(item)
else:
    print("Files not found")
