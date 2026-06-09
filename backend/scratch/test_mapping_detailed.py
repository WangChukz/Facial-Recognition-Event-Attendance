import pandas as pd
import os
import sys
import unicodedata
import re
import json

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def remove_vietnamese_diacritics(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = text.replace('đ', 'd').replace('Đ', 'D')
    text = unicodedata.normalize('NFC', text)
    text = text.replace(' ', '')
    return text

meta_path = "c:/AI_event/dataset/dataset/metadata.xlsx"
real_dir = "c:/AI_event/dataset/dataset/real"
enroll_dir = "c:/AI_event/dataset/dataset/enroll"

if not os.path.exists(meta_path) or not os.path.exists(real_dir) or not os.path.exists(enroll_dir):
    print("Files not found")
    sys.exit(1)

df = pd.read_excel(meta_path)
real_folders = sorted([d for d in os.listdir(real_dir) if os.path.isdir(os.path.join(real_dir, d))])
enroll_files = sorted([f for f in os.listdir(enroll_dir) if os.path.isfile(os.path.join(enroll_dir, f))])

# Map metadata
meta_map = {}
for idx, row in df.iterrows():
    name = row['Họ và tên']
    sid = str(row['Mã sinh viên']).strip()
    sclass = str(row['Lớp']).strip()
    dob = str(row['Ngày sinh']).split()[0]
    
    clean_name = remove_vietnamese_diacritics(name).lower()
    meta_map[clean_name] = {
        "sid": sid,
        "name": name,
        "class": sclass,
        "dob": dob
    }

print("=== CHECK MAPPING BETWEEN REAL FOLDERS AND ENROLL FILES ===")
unmatched_real = []
matched_count = 0

for rf in real_folders:
    # BuiDucThinh_real -> buiducthinh
    rf_clean = rf.replace('_real', '').lower()
    
    # Check match in enroll files
    # Tìm file enroll khớp với rf_clean
    matched_ef = None
    for ef in enroll_files:
        ef_clean = re.sub(r'_enroll\.(jpg|png|jpeg|webp|bmp)', '', ef, flags=re.IGNORECASE).lower()
        if ef_clean == rf_clean:
            matched_ef = ef
            break
            
    # Check match in metadata
    meta_info = meta_map.get(rf_clean)
    
    # Xử lý trường hợp đặc biệt: PhamTrungKien vs NguyenTrungKien
    if not meta_info and rf_clean == "phamtrungkien":
        meta_info = meta_map.get("nguyentrungkien")
        if meta_info:
            print(f"-> Ánh xạ đặc biệt: Folder '{rf}' khớp với Sinh viên '{meta_info['name']}' ({meta_info['sid']}) trong metadata")
            
    if not matched_ef and rf_clean == "phamtrungkien":
        # Check if NguyenTrungKien_enroll.png matches
        for ef in enroll_files:
            ef_clean = re.sub(r'_enroll\.(jpg|png|jpeg|webp|bmp)', '', ef, flags=re.IGNORECASE).lower()
            if ef_clean == "nguyentrungkien":
                matched_ef = ef
                print(f"-> Ánh xạ đặc biệt: Folder '{rf}' khớp với File Enroll '{ef}'")
                break

    if meta_info and matched_ef:
        matched_count += 1
    else:
        print(f"Không khớp hoàn toàn cho folder '{rf}': Matched EF: {matched_ef}, Matched Meta: {meta_info is not None}")
        unmatched_real.append(rf)

print(f"\nTổng kết khớp 3 chiều (Folder Real <-> File Enroll <-> Metadata): {matched_count}/39")
