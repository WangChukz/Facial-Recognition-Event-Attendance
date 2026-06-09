import os
import sys
import argparse
import json
import time
import logging
import unicodedata
import re
import pandas as pd
from typing import Tuple, Dict, List

# Tu dong reconfigure encoding de tranh loi Unicode tren Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import cv2
import numpy as np
import joblib


# Thiết lập Logger để hiển thị tiến trình đẹp mắt và chuyên nghiệp
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("SVM_Trainer")

# Tự động thêm thư mục 'backend' vào sys.path để chạy script từ bất kỳ đâu không bị lỗi ModuleNotFoundError
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)
    logger.info(f"Đã cấu hình PYTHONPATH: {backend_dir}")

try:
    from app.services.face_pipeline import FacePipeline
    from app.services.augmentation import (
        crop_face_with_margin,
        GEO_AUG,
        PHOTO_AUG,
        COMBINED_AUG,
        OCC_AUG
    )
except ModuleNotFoundError as e:
    logger.error("Không tìm thấy các module app.services. Hãy chắc chắn bạn đang chạy script trong môi trường ảo của dự án.")
    logger.error(str(e))
    sys.exit(1)

from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix


def parse_args():
    parser = argparse.ArgumentParser(description="Kịch bản huấn luyện SVM Classifier cho Sinh viên Học viện Ngân hàng.")
    parser.add_argument(
        "--data_dir",
        type=str,
        default="c:/AI_event/dataset_students",
        help="Đường dẫn tới thư mục chứa dataset sinh viên (mỗi sinh viên là 1 thư mục con)."
    )
    parser.add_argument(
        "--model_out",
        type=str,
        default=os.path.join(backend_dir, "app", "models", "student_svm_classifier.pkl"),
        help="Đường dẫn lưu file model SVM (.pkl)."
    )
    parser.add_argument(
        "--label_out",
        type=str,
        default=os.path.join(backend_dir, "app", "models", "label_encoder.json"),
        help="Đường dẫn lưu file map nhãn học sinh (.json)."
    )
    parser.add_argument(
        "--augment",
        type=bool,
        default=False,
        help="Có sử dụng Data Augmentation để tăng kích thước tập dữ liệu không."
    )
    parser.add_argument(
        "--test_size",
        type=float,
        default=0.2,
        help="Tỉ lệ chia tập kiểm thử (Validation/Test)."
    )
    return parser.parse_args()


def process_and_extract(data_dir: str, pipeline: FacePipeline, use_augment: bool) -> Tuple[np.ndarray, np.ndarray, Dict[int, dict]]:
    """
    Quét qua toàn bộ thư mục sinh viên, tiền xử lý, tăng cường dữ liệu và trích xuất vector embeddings 512-D.
    """
    X = []
    y = []
    label_map = {}

    if not os.path.exists(data_dir):
        logger.error(f"Thư mục dataset không tồn tại: {data_dir}")
        logger.info("Hãy tạo thư mục và đưa dữ liệu sinh viên vào theo cấu trúc:")
        logger.info(f"  {data_dir}/SV001_NguyenVanA/image1.jpg")
        logger.info(f"  {data_dir}/SV002_TranThiB/image1.jpg")
        raise FileNotFoundError(f"Không tìm thấy thư mục {data_dir}")

    # Tìm kiếm và tải file metadata.xlsx để ánh xạ thông tin
    meta_path = "c:/AI_event/dataset/dataset/metadata.xlsx"
    if not os.path.exists(meta_path):
        meta_path = os.path.join(os.path.dirname(data_dir), "metadata.xlsx")
        
    meta_map = {}
    if os.path.exists(meta_path):
        try:
            df_meta = pd.read_excel(meta_path)
            logger.info(f"Đã nạp file metadata thành công từ: {meta_path} (Tìm thấy {len(df_meta)} sinh viên trong danh sách)")
            
            def remove_vietnamese_diacritics(text):
                if not isinstance(text, str):
                    return ""
                text = unicodedata.normalize('NFD', text)
                text = re.sub(r'[\u0300-\u036f]', '', text)
                text = text.replace('đ', 'd').replace('Đ', 'D')
                text = unicodedata.normalize('NFC', text)
                text = text.replace(' ', '')
                return text

            for _, row in df_meta.iterrows():
                name = str(row.get('Họ và tên', '')).strip()
                student_id = str(row.get('Mã sinh viên', '')).strip()
                sclass = str(row.get('Lớp', '')).strip()
                # Định dạng ngày sinh dạng chuỗi YYYY-MM-DD
                dob = str(row.get('Ngày sinh', '')).strip().split()[0] if row.get('Ngày sinh') else ""
                
                clean_name = remove_vietnamese_diacritics(name).lower()
                meta_map[clean_name] = {
                    "student_id": student_id,
                    "name": name,
                    "class": sclass,
                    "dob": dob
                }
        except Exception as e:
            logger.error(f"Lỗi khi đọc file metadata: {str(e)}")
    else:
        logger.warning(f"Không tìm thấy file metadata.xlsx tại: {meta_path}. Sẽ sử dụng fallback thông tin từ tên thư mục.")

    # Lấy danh sách các thư mục sinh viên (loại bỏ file ẩn/hệ thống)
    student_folders = sorted([
        f for f in os.listdir(data_dir) 
        if os.path.isdir(os.path.join(data_dir, f)) and not f.startswith(".")
    ])

    if not student_folders:
        logger.error(f"Thư mục '{data_dir}' rỗng. Hãy copy dữ liệu sinh viên vào trước khi chạy huấn luyện.")
        sys.exit(1)

    logger.info(f"Phát hiện tổng cộng {len(student_folders)} thư mục sinh viên.")

    for idx, folder in enumerate(student_folders):
        # Sửa lỗi so khớp không dấu và biệt lệ PhamTrungKien -> Nguyễn Trung Kiên
        clean_folder = folder.replace("_real", "").lower()
        if clean_folder == "phamtrungkien":
            clean_folder = "nguyentrungkien"
            
        student_info = meta_map.get(clean_folder)
        if student_info:
            label_map[idx] = {
                "student_id": student_info["student_id"],
                "name": student_info["name"],
                "class": student_info["class"],
                "dob": student_info["dob"],
                "folder_name": folder,
                "clean_name": folder.replace("_real", "")
            }
            logger.info(f"[{idx + 1}/{len(student_folders)}] Khớp thành công: Folder '{folder}' -> SV '{student_info['name']}' ({student_info['student_id']})")
        else:
            label_map[idx] = {
                "student_id": folder.replace("_real", ""),
                "name": folder.replace("_real", ""),
                "class": "Unknown",
                "dob": "",
                "folder_name": folder,
                "clean_name": folder.replace("_real", "")
            }
            logger.warning(f"[{idx + 1}/{len(student_folders)}] Không tìm thấy metadata cho folder: '{folder}'")
            
        folder_path = os.path.join(data_dir, folder)
        
        # Hỗ trợ nhiều định dạng ảnh phổ biến và duyệt đệ quy (hỗ trợ cả các folder con lồng nhau)
        valid_extensions = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
        images = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(valid_extensions):
                    images.append(os.path.join(root, file))

        logger.info(f"  -> Thư mục chứa {len(images)} ảnh gốc.")


        if not images:
            logger.warning(f"  -> Thư mục '{folder}' không chứa hình ảnh hợp lệ nào. Bỏ qua.")
            continue

        for img_path in images:
            img_name = os.path.basename(img_path)
            img_array = np.fromfile(img_path, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is None:
                logger.warning(f"  -> Lỗi không thể đọc ảnh (giải mã thất bại): {img_name}")
                continue

            # Bước 1: Trích xuất ảnh gốc trước
            try:
                faces = pipeline.process_frame_sync(img, use_adaptive_clahe=True)
                v = pipeline.validate_single_face(faces, min_det=0.60, min_face_size=80)
                
                if not v["ok"]:
                    logger.warning(f"  -> Ảnh '{img_name}' không vượt qua cổng chất lượng: {v['reason']}")
                    continue

                face = v["face"]
                # Lưu embedding của ảnh gốc
                X.append(face["embedding"])
                y.append(idx)

                # Cắt mặt để làm đầu vào cho Augmentations chuyên sâu
                face_crop = crop_face_with_margin(img, face["bbox"], margin=0.25)
                
                # Bước 2: Tăng cường dữ liệu (nếu bật chế độ augment)
                if use_augment:
                    # Các pipeline tăng cường có sẵn
                    configs = [
                        (GEO_AUG, 5),      # Sinh 5 ảnh biến đổi hình học
                        (PHOTO_AUG, 5),    # Sinh 5 ảnh biến đổi ánh sáng
                        (COMBINED_AUG, 3), # Sinh 3 ảnh biến đổi kết hợp
                        (OCC_AUG, 2)       # Sinh 2 ảnh giả lập khẩu trang/kính
                    ]
                    
                    for aug_pipe, count in configs:
                        for c_idx in range(count):
                            try:
                                aug_res = aug_pipe(image=face_crop)
                                aug_img = aug_res["image"]
                                
                                # Đưa ảnh tăng cường qua InsightFace để lấy vector mới
                                aug_faces = pipeline.process_frame_sync(aug_img, use_adaptive_clahe=True)
                                if aug_faces:
                                    # Lấy khuôn mặt có chất lượng cao nhất trong ảnh augment
                                    aug_faces.sort(key=lambda x: x["det_score"], reverse=True)
                                    X.append(aug_faces[0]["embedding"])
                                    y.append(idx)
                            except Exception as ex:
                                continue
            except Exception as e:
                logger.error(f"  -> Lỗi khi xử lý ảnh {img_name}: {str(e)}")
                continue

    return np.array(X), np.array(y), label_map


def main():
    args = parse_args()
    
    logger.info("=== HỆ THỐNG HUẤN LUYỆN SVM CHO SINH VIÊN HỌC VIỆN NGÂN HÀNG ===")
    logger.info(f"Đường dẫn dataset: {args.data_dir}")
    logger.info(f"Có tăng cường ảnh (Augmentation): {args.augment}")
    
    # Khởi tạo Face Pipeline của dự án
    logger.info("Đang khởi tạo mô hình trích xuất đặc trưng InsightFace ArcFace...")
    pipeline = FacePipeline()
    
    t_start = time.time()
    
    # Thực hiện tiền xử lý & trích xuất vector
    try:
        X, y, label_map = process_and_extract(args.data_dir, pipeline, args.augment)
    except FileNotFoundError:
        sys.exit(1)
        
    if len(X) == 0:
        logger.error("Không trích xuất được bất kỳ khuôn mặt hợp lệ nào từ dataset. Vui lòng kiểm tra lại chất lượng ảnh đầu vào.")
        sys.exit(1)
        
    logger.info(f"Quá trình trích xuất hoàn tất! Tổng cộng thu về: {X.shape[0]} vector đặc trưng (512 chiều).")
    
    # Chuẩn hóa L2 cho tất cả các vector đặc trưng để đưa về mặt cầu đơn vị
    import faiss
    X_norm = np.array(X, dtype=np.float32)
    faiss.normalize_L2(X_norm)
    X = X_norm
    
    # Đảm bảo mỗi sinh viên có ít nhất 2 mẫu (tránh crash khi train_test_split với stratify)
    unique_labels, counts = np.unique(y, return_counts=True)
    for label, count in zip(unique_labels, counts):
        if count < 2:
            logger.warning(f"Sinh viên '{label_map[label]}' chỉ có {count} mẫu đặc trưng. Đang tự động nhân bản để tránh lỗi phân chia tập dữ liệu.")
            indices = np.where(y == label)[0]
            for idx_to_dup in indices:
                X = np.vstack([X, X[idx_to_dup]])
                y = np.append(y, label)
    
    # Phân chia dữ liệu train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, 
        test_size=args.test_size, 
        random_state=42, 
        stratify=y
    )
    logger.info(f"Đã phân chia tập dữ liệu: Train = {X_train.shape[0]} mẫu, Test = {X_test.shape[0]} mẫu.")
    
    # Huấn luyện bộ phân lớp SVM
    logger.info("Đang cấu hình và huấn luyện mô hình SVM Classifier (Kernel RBF, Probability=True)...")
    # C=2.0 tăng độ phạt lỗi để phân tách sinh viên tốt hơn, probability=True để xuất ra xác suất %
    svm_model = SVC(kernel='rbf', C=2.0, gamma='scale', probability=True, random_state=42)
    
    svm_start = time.time()
    svm_model.fit(X_train, y_train)
    logger.info(f"Đã huấn luyện xong SVM trong {time.time() - svm_start:.2f} giây!")
    
    # Đánh giá hiệu năng mô hình
    y_pred = svm_model.predict(X_test)
    accuracy = np.mean(y_pred == y_test)
    
    logger.info("\n" + "="*50)
    logger.info(f"ĐỘ CHÍNH XÁC TẬP KIỂM THỬ (TEST SET ACCURACY): {accuracy * 100:.2f}%")
    logger.info("="*50 + "\n")
    
    # In báo cáo phân lớp chi tiết (chỉ cho các lớp thực tế xuất hiện trong dữ liệu)
    present_classes = sorted(list(set(y)))
    target_names = [
        label_map[c]["name"] if isinstance(label_map[c], dict) else str(label_map[c]) 
        for c in present_classes
    ]
    logger.info("BÁO CÁO PHÂN LỚP CHI TIẾT (CLASSIFICATION REPORT):")
    print(classification_report(y_test, y_pred, labels=present_classes, target_names=target_names))
    
    # Lưu Model ra file .pkl
    os.makedirs(os.path.dirname(args.model_out), exist_ok=True)
    joblib.dump(svm_model, args.model_out)
    logger.info(f"Đã lưu mô hình SVM tại: {args.model_out}")
    
    # Lưu tập dữ liệu split để làm cơ sở A/B test đánh giá so sánh
    split_out = os.path.join(os.path.dirname(args.model_out), "dataset_split.npz")
    np.savez(split_out, X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test)
    logger.info(f"Đã lưu tập đặc trưng split tại: {split_out}")
    
    # Lưu Label encoder ra file .json
    with open(args.label_out, 'w', encoding='utf-8') as f:
        json.dump(label_map, f, ensure_ascii=False, indent=4)
    logger.info(f"Đã lưu mã hóa nhãn tại: {args.label_out}")
    
    total_time = time.time() - t_start
    logger.info(f"=== TOÀN BỘ QUÁ TRÌNH HOÀN TẤT SAU {total_time:.2f} GIÂY ===")
    logger.info("Hệ thống đã sẵn sàng cho nhận diện sinh viên Học viện Ngân hàng thời gian thực!")


if __name__ == "__main__":
    main()
