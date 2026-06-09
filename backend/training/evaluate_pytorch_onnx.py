import os
import sys
import time
import json
import logging
from typing import Tuple, List

import cv2
import numpy as np
import onnxruntime as ort
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

# Đảm bảo UTF-8 hiển thị mượt mà trên console Windows
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
logger = logging.getLogger("PyTorch_ONNX_Evaluator")

def preprocess_image(img_path: str) -> np.ndarray:
    """Đọc ảnh và tiền xử lý theo chuẩn ImageNet (giống pipeline huấn luyện PyTorch)."""
    img = cv2.imread(img_path)
    if img is None:
        return None
    # BGR -> RGB
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # Resize về 224x224
    img = cv2.resize(img, (224, 224))
    # Chuyển về float32 và chuẩn hóa 0-1
    img = img.astype(np.float32) / 255.0
    # Chuẩn hóa ImageNet mean & std
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img = (img - mean) / std
    # HWC -> CHW
    img = img.transpose((2, 0, 1))
    # Thêm batch dimension -> [1, 3, 224, 224]
    img = np.expand_dims(img, axis=0)
    return img

def main():
    data_dir = "c:/AI_event/dataset_students"
    onnx_path = "c:/AI_event/AI_Project_2526/backend/app/models/student_resnet18_arcface.onnx"
    label_path = "c:/AI_event/AI_Project_2526/backend/app/models/label_encoder_pytorch.json"

    if not os.path.exists(onnx_path) or not os.path.exists(label_path):
        logger.error("Không tìm thấy mô hình ONNX hoặc file nhãn lớp. Vui lòng chạy huấn luyện trước.")
        sys.exit(1)

    with open(label_path, 'r', encoding='utf-8') as f:
        label_map = {int(k): v for k, v in json.load(f).items()}

    logger.info("=== BẮT ĐẦU ĐÁNH GIÁ MÔ HÌNH TINH CHỈNH PYTORCH ONNX ===")
    logger.info(f"Đang tải mô hình ONNX: {onnx_path}")
    
    # Khởi chạy session ONNX Runtime
    session = ort.InferenceSession(onnx_path, providers=['CPUExecutionProvider'])
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    # Quét tập dữ liệu
    image_paths = []
    labels = []
    
    student_folders = sorted([
        f for f in os.listdir(data_dir) 
        if os.path.isdir(os.path.join(data_dir, f)) and not f.startswith(".")
    ])

    for idx, folder in enumerate(student_folders):
        folder_path = os.path.join(data_dir, folder)
        valid_extensions = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(valid_extensions):
                    image_paths.append(os.path.join(root, file))
                    labels.append(idx)

    logger.info(f"Đã quét xong: {len(image_paths)} ảnh từ {len(student_folders)} sinh viên.")

    # Trích xuất embeddings
    embeddings = []
    valid_labels = []
    inference_times = []

    logger.info("Đang trích xuất vector đặc trưng bằng mô hình ONNX...")
    for idx, img_path in enumerate(image_paths):
        processed = preprocess_image(img_path)
        if processed is None:
            continue
        
        t0 = time.perf_counter()
        # Chạy inference ONNX
        outputs = session.run([output_name], {input_name: processed})
        t_elapsed = (time.perf_counter() - t0) * 1000 # ms
        
        emb = outputs[0][0]
        # Chuẩn hóa L2 vector đặc trưng
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
            
        embeddings.append(emb)
        valid_labels.append(labels[idx])
        inference_times.append(t_elapsed)

    X = np.array(embeddings, dtype=np.float32)
    y = np.array(valid_labels, dtype=np.int32)
    
    logger.info(f"Trích xuất hoàn tất! Số vector: {X.shape[0]}, Kích thước: {X.shape[1]}")
    logger.info(f"Độ trễ suy luận trung bình trên CPU: {np.mean(inference_times):.2f} ms")

    # Đảm bảo mỗi sinh viên có ít nhất 2 mẫu (tránh crash khi train_test_split với stratify)
    unique_labels, counts = np.unique(y, return_counts=True)
    for label, count in zip(unique_labels, counts):
        if count < 2:
            logger.warning(f"Sinh viên '{label_map[label]}' chỉ có {count} mẫu đặc trưng. Đang tự động nhân bản để tránh lỗi phân chia tập dữ liệu.")
            indices = np.where(y == label)[0]
            for idx_to_dup in indices:
                X = np.vstack([X, X[idx_to_dup]])
                y = np.append(y, label)

    # Chia tập Train/Test theo tỉ lệ 80% / 20%
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Đánh giá bằng bộ phân lớp so khớp Cosine Similarity gần nhất (1-NN)
    correct_predictions = 0
    y_pred = []

    for i, test_emb in enumerate(X_test):
        # Tính cosine similarity giữa test embedding và toàn bộ train embeddings
        # Vì cả hai đều đã chuẩn hóa L2, tích vô hướng chính là cosine similarity
        similarities = np.dot(X_train, test_emb)
        best_match_idx = np.argmax(similarities)
        pred_label = y_train[best_match_idx]
        y_pred.append(pred_label)

    accuracy = accuracy_score(y_test, y_pred)
    
    print("\n" + "="*70)
    print(f"   KẾT QUẢ ĐÁNH GIÁ MÔ HÌNH PYTORCH ARCFACE ONNX (1-NN COSINE MATCHING)")
    print("="*70)
    print(f"Tổng số ảnh kiểm thử (Test set): {len(y_test)}")
    print(f"Dự đoán đúng: {np.sum(y_test == y_pred)} / {len(y_test)}")
    print(f"Độ chính xác (Accuracy): {accuracy * 100:.2f}%")
    print(f"Tốc độ suy luận mạng neuron (Latency): {np.mean(inference_times):.2f} ms / ảnh")
    print("="*70 + "\n")

    # In báo cáo phân lớp chi tiết
    labels_list = sorted(list(label_map.keys()))
    target_names = [label_map[i] for i in labels_list]
    print("BÁO CÁO PHÂN LỚP CHI TIẾT:")
    print(classification_report(y_test, y_pred, labels=labels_list, target_names=target_names, zero_division=0))

if __name__ == "__main__":
    main()
