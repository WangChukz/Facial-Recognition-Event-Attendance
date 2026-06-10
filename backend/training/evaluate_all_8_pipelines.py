import os
import sys
import time
import json
import logging
import re
import unicodedata
import pandas as pd
from typing import Tuple, List, Dict, Any

import cv2
import numpy as np
import onnxruntime as ort
import faiss
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

# Tự động thêm PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Đảm bảo UTF-8 trên Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("6_Pipeline_RealWorld_Benchmark")

from app.ai_core.pipeline import FacePipeline
from app.ai_core.utils.augmentation import (
    crop_face_with_margin,
    validate_face_size,
    GEO_AUG,
    PHOTO_AUG,
    COMBINED_AUG,
    OCC_AUG
)

def preprocess_image_resnet18(img: np.ndarray) -> np.ndarray:
    """Tiền xử lý ảnh theo chuẩn ImageNet cho mô hình ResNet-18."""
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (224, 224))
    img = img.astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img = (img - mean) / std
    img = img.transpose((2, 0, 1))
    img = np.expand_dims(img, axis=0)
    return img

def extract_resnet18_single(img: np.ndarray, session, input_name, output_name) -> np.ndarray:
    """Trích xuất embedding đơn bằng mô hình ResNet-18 ONNX."""
    processed = preprocess_image_resnet18(img)
    outputs = session.run([output_name], {input_name: processed})
    return outputs[0][0]

def main():
    train_dir = "c:/AI_event/dataset/dataset/enroll"
    test_dir = "c:/AI_event/dataset/dataset/real"
    meta_path = "c:/AI_event/dataset/dataset/metadata.xlsx"
    onnx_path = "c:/AI_event/AI_Project_2526/backend/app/models/student_resnet18_arcface.onnx"
    
    if not os.path.exists(train_dir) or not os.path.exists(test_dir):
        logger.error("Không tìm thấy các thư mục dataset. Vui lòng chạy tiền xử lý trước.")
        sys.exit(1)
        
    # Khởi tạo pipeline gốc và custom ONNX session
    pipeline = FacePipeline()
    session = ort.InferenceSession(onnx_path, providers=['CPUExecutionProvider'])
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    # Đọc metadata để đồng bộ lớp
    meta_map = {}
    if os.path.exists(meta_path):
        try:
            df_meta = pd.read_excel(meta_path)
            logger.info(f"Đã nạp file metadata thành công: {meta_path} (Tìm thấy {len(df_meta)} sinh viên)")
            
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
                clean_name = remove_vietnamese_diacritics(name).lower()
                meta_map[clean_name] = {
                    "student_id": str(row.get('Mã sinh viên', '')).strip(),
                    "name": name,
                    "class": str(row.get('Lớp', '')).strip()
                }
        except Exception as e:
            logger.error(f"Lỗi khi đọc file metadata trong Evaluation: {str(e)}")
            
    # Lập bản đồ nhãn lớp thống nhất dựa trên 39 sinh viên từ metadata
    # Sắp xếp theo thứ tự bảng chữ cái của tên không dấu tiếng Việt
    student_keys = sorted(list(meta_map.keys()))
    class_map = {name: idx for idx, name in enumerate(student_keys)}
    
    # ------------------ 1. TRÍCH XUẤT TẬP HUẤN LUYỆN (ENROLL + AUGMENTATION) ------------------
    logger.info("--- Bắt đầu trích xuất tập huấn luyện (Enroll + Data Augmentation) ---")
    
    X_train_orig_list, y_train_orig_list = [], []
    X_train_ft_list, y_train_ft_list = [], []
    
    valid_extensions = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
    enroll_files = [f for f in os.listdir(train_dir) if f.lower().endswith(valid_extensions)]
    
    logger.info(f"Tìm thấy {len(enroll_files)} file ảnh enroll.")
    
    for ef in enroll_files:
        # Tách tên clean từ file (ví dụ: BuiDucThinh_enroll.jpg -> buiducthinh)
        ef_clean = re.sub(r'_enroll\.(jpg|png|jpeg|webp|bmp)', '', ef, flags=re.IGNORECASE).lower()
        
        if ef_clean not in class_map:
            logger.warning(f"File enroll '{ef}' (clean: '{ef_clean}') không khớp với bất kỳ sinh viên nào trong metadata. Bỏ qua.")
            continue
            
        class_id = class_map[ef_clean]
        img_path = os.path.join(train_dir, ef)
        img_array = np.fromfile(img_path, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            logger.warning(f"Không thể giải mã ảnh: {img_path}")
            continue
            
        # 1. Xử lý ảnh gốc
        try:
            faces = pipeline.process_frame_sync(img, use_adaptive_clahe=True)
            v = pipeline.validate_single_face(faces, min_det=0.50, min_face_size=60)
            if v["ok"]:
                face = v["face"]
                # Lưu đặc trưng gốc ResNet-50
                X_train_orig_list.append(face["embedding"])
                y_train_orig_list.append(class_id)
                
                # Cắt mặt để làm đầu vào cho custom ResNet-18 và Augmentation
                face_crop = crop_face_with_margin(img, face["bbox"], margin=0.25)
                
                # Lưu đặc trưng gốc ResNet-18
                emb_ft = extract_resnet18_single(face_crop, session, input_name, output_name)
                X_train_ft_list.append(emb_ft)
                y_train_ft_list.append(class_id)
                
                # 2. Sinh thêm 15 ảnh tăng cường giống như kịch bản chạy thực tế
                configs = [
                    (GEO_AUG, 5),      # Hình học
                    (PHOTO_AUG, 5),    # Ánh sáng
                    (COMBINED_AUG, 3), # Kết hợp
                    (OCC_AUG, 2)       # Giả lập che khuất
                ]
                
                for aug_pipe, count in configs:
                    for _ in range(count):
                        try:
                            aug_res = aug_pipe(image=face_crop)
                            aug_img = aug_res["image"]
                            
                            # Trích xuất với ResNet-50 gốc
                            aug_faces = pipeline.process_frame_sync(aug_img, use_adaptive_clahe=True)
                            if aug_faces:
                                aug_faces.sort(key=lambda x: x["det_score"], reverse=True)
                                X_train_orig_list.append(aug_faces[0]["embedding"])
                                y_train_orig_list.append(class_id)
                                
                            # Trích xuất với ResNet-18 custom
                            emb_ft_aug = extract_resnet18_single(aug_img, session, input_name, output_name)
                            X_train_ft_list.append(emb_ft_aug)
                            y_train_ft_list.append(class_id)
                        except Exception:
                            continue
            else:
                logger.warning(f"Ảnh enroll {ef} không vượt qua cổng chất lượng: {v['reason']}")
        except Exception as e:
            logger.warning(f"Lỗi khi xử lý ảnh đăng ký của {ef}: {str(e)}")
            continue

    X_train_orig = np.array(X_train_orig_list, dtype=np.float32)
    y_train_orig = np.array(y_train_orig_list, dtype=np.int32)
    X_train_ft = np.array(X_train_ft_list, dtype=np.float32)
    y_train_ft = np.array(y_train_ft_list, dtype=np.int32)
    
    # ------------------ 2. TRÍCH XUẤT TẬP KIỂM THỬ THỰC TẾ (REAL) ------------------
    logger.info("--- Bắt đầu trích xuất tập kiểm thử thực tế (Real) ---")
    
    X_test_orig_list, y_test_orig_list = [], []
    X_test_ft_list, y_test_ft_list = [], []
    
    real_folders = [f for f in os.listdir(test_dir) if os.path.isdir(os.path.join(test_dir, f)) and not f.startswith(".")]
    
    for r_folder in real_folders:
        clean_name = r_folder.replace("_real", "").lower()
        # Ánh xạ đặc biệt cho biệt lệ PhamTrungKien -> nguyentrungkien
        if clean_name == "phamtrungkien":
            clean_name = "nguyentrungkien"
            
        if clean_name not in class_map:
            logger.warning(f"Folder thực tế '{r_folder}' (clean: '{clean_name}') không khớp với bất kỳ sinh viên nào. Bỏ qua.")
            continue
            
        class_id = class_map[clean_name]
        folder_path = os.path.join(test_dir, r_folder)
        
        test_files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)]
        
        for t_file in test_files:
            t_path = os.path.join(folder_path, t_file)
            img_array = np.fromfile(t_path, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is None:
                continue
                
            try:
                # 1. Trích xuất với ResNet-50 gốc
                faces = pipeline.process_frame_sync(img, use_adaptive_clahe=True)
                v = pipeline.validate_single_face(faces, min_det=0.50, min_face_size=60)
                if v["ok"]:
                    face = v["face"]
                    X_test_orig_list.append(face["embedding"])
                    y_test_orig_list.append(class_id)
                    
                    # Cắt mặt cho ResNet-18
                    face_crop = crop_face_with_margin(img, face["bbox"], margin=0.25)
                    emb_ft = extract_resnet18_single(face_crop, session, input_name, output_name)
                    X_test_ft_list.append(emb_ft)
                    y_test_ft_list.append(class_id)
            except Exception:
                continue

    X_test_orig = np.array(X_test_orig_list, dtype=np.float32)
    y_test_orig = np.array(y_test_orig_list, dtype=np.int32)
    X_test_ft = np.array(X_test_ft_list, dtype=np.float32)
    y_test_ft = np.array(y_test_ft_list, dtype=np.int32)
    
    logger.info(f"Đã chuẩn bị xong dữ liệu đối chứng:")
    logger.info(f"  - Train Set (Orig): {X_train_orig.shape[0]} mẫu | Train Set (FT): {X_train_ft.shape[0]} mẫu")
    logger.info(f"  - Test Set (Orig): {X_test_orig.shape[0]} mẫu | Test Set (FT): {X_test_ft.shape[0]} mẫu")
    
    # Chuẩn hóa L2 cho các tập vector đặc trưng
    faiss.normalize_L2(X_train_orig)
    faiss.normalize_L2(X_test_orig)
    faiss.normalize_L2(X_train_ft)
    faiss.normalize_L2(X_test_ft)
    cache_path = os.path.join(current_dir, "results", "scenario_embeddings_cache.npz")
    np.savez_compressed(
        cache_path,
        X_train_orig=X_train_orig,
        y_train_orig=y_train_orig,
        X_test_orig=X_test_orig,
        y_test_orig=y_test_orig,
        X_train_ft=X_train_ft,
        y_train_ft=y_train_ft,
        X_test_ft=X_test_ft,
        y_test_ft=y_test_ft,
    )
    logger.info(f"Da luu cache embedding danh gia tai: {cache_path}")
    
    # ------------------ 3. THỰC THI CHẠY ĐỐI CHỨNG 4 LUỒNG ------------------
    def run_evaluation(X_tr: np.ndarray, X_te: np.ndarray, y_tr: np.ndarray, y_te: np.ndarray, head_type: str) -> Tuple[float, float, float, float, float, float]:
        t0 = time.perf_counter()
        scores = []

        if head_type == "faiss":
            index = faiss.IndexFlatIP(512)
            index.add(X_tr)
            distances, ids = index.search(X_te, 1)
            y_pred = [y_tr[i] if i != -1 else -1 for i in ids.flatten()]
            scores = [float(1.0 - (d / 2.0)) for d in distances.flatten()]
        elif head_type == "hnsw":
            index = faiss.IndexHNSWFlat(512, 32)
            index.hnsw.efConstruction = 200
            index.hnsw.efSearch = 64
            index.add(X_tr)
            sims, ids = index.search(X_te, 1)
            y_pred = [y_tr[i] if i != -1 else -1 for i in ids.flatten()]
            scores = [float(s) for s in sims.flatten()]
        else:
            raise ValueError(f"Unsupported head_type: {head_type}")
            
        latency_ms = ((time.perf_counter() - t0) / len(X_te)) * 1000
        acc = accuracy_score(y_te, y_pred) * 100
        precision = precision_score(y_te, y_pred, average='weighted', zero_division=0) * 100
        recall = recall_score(y_te, y_pred, average='weighted', zero_division=0) * 100
        f1 = f1_score(y_te, y_pred, average='weighted', zero_division=0) * 100
        avg_score = float(np.mean(scores)) if scores else 0.0
        return acc, precision, recall, f1, avg_score, latency_ms

    results = []
    configs = [
        # Nhóm A: ArcFace Gốc (ResNet-50)
        ("Luồng 1: ArcFace Gốc + FAISS", X_train_orig, X_test_orig, y_train_orig, y_test_orig, "faiss", "ArcFace Gốc (ResNet-50)"),
        ("Luồng 2: ArcFace Gốc + HNSW", X_train_orig, X_test_orig, y_train_orig, y_test_orig, "hnsw", "ArcFace Gốc (ResNet-50)"),
        # Nhóm B: ArcFace Tinh chỉnh (ResNet-18)
        ("Luồng 3: ArcFace Tinh chỉnh + FAISS", X_train_ft, X_test_ft, y_train_ft, y_test_ft, "faiss", "ResNet-18 ArcFace FT"),
        ("Luồng 4: ArcFace Tinh chỉnh + HNSW", X_train_ft, X_test_ft, y_train_ft, y_test_ft, "hnsw", "ResNet-18 ArcFace FT"),
    ]

    for name, X_tr, X_te, y_tr, y_te, head, model_desc in configs:
        logger.info(f"Đang thực thi đánh giá {name}...")
        acc, precision, recall, f1, avg_score, head_lat = run_evaluation(X_tr, X_te, y_tr, y_te, head)
        
        # Cộng thêm thời gian chạy mạng neuron (ResNet-50: 58.4ms, ResNet-18: 12.05ms)
        net_lat = 12.05 if "FT" in model_desc else 58.40
        total_lat = head_lat + net_lat
        
        results.append({
            "name": name,
            "backbone": model_desc,
            "head": head.upper(),
            "accuracy": f"{acc:.2f}%",
            "precision": f"{precision:.2f}%",
            "recall": f"{recall:.2f}%",
            "latency": f"{total_lat:.3f} ms",
            "head_latency": f"{head_lat:.4f} ms",
            "f1_score": f"{f1:.2f}%",
            "similarity_avg": f"{avg_score:.4f}",
            "test_samples": int(len(y_te)),
            "correct_predictions": int(round(acc * len(y_te) / 100))
        })
        
    # In bảng kết quả đối chứng thực tế
    print("\n" + "="*95)
    print("                BẢNG THỰC NGHIỆM ĐỐI CHIẾU HIỆU NĂNG THỰC TẾ TRÊN TẬP HÌNH ẢNH LỚP HỌC (REAL)")
    print("="*95)
    print(f"{'Luồng Thực Nghiệm':<36} | {'Mô hình Backbone':<22} | {'Độ chính xác':<12} | {'Độ trễ trung bình':<17}")
    print("-"*95)
    for r in results:
        print(f"{r['name']:<36} | {r['backbone']:<22} | {r['accuracy']:<12} | {r['latency']:<17}")
    print("="*95 + "\n")
    
    # Ghi đè vào tệp JSON kết quả để cập nhật tệp Word tự động
    res_path = os.path.join(current_dir, "results", "benchmark_results.json")
    with open(res_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    logger.info(f"Đã lưu kết quả đối chứng thực tế mới tại: {res_path}")

if __name__ == "__main__":
    main()
