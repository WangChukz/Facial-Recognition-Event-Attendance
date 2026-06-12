"""
enrollment_v2.py — Enhanced enrollment with data augmentation.
Generates multiple embeddings from single enrollment image to improve recognition accuracy.
"""
from typing import List
import cv2
import numpy as np

from app.services.augmentation import (
    assess_image_quality,
    crop_face_with_margin,
    validate_face_size,
    filter_embeddings,
    GEO_AUG,
    PHOTO_AUG,
    OCC_AUG,
    COMBINED_AUG,
)


def generate_augmented_embeddings(
    image: np.ndarray,
    process_face_fn,
    n_geometric: int = 7,
    n_photo: int = 5,
    n_combined: int = 2,
    n_occlusion: int = 2,
) -> List[np.ndarray]:
    """
    Tạo nhiều vector đặc trưng khuôn mặt (embeddings) từ một ảnh gốc đăng ký bằng phương pháp tăng cường dữ liệu (augmentation).
    Quy trình này giúp tạo ra nhiều biến thể của khuôn mặt để tăng độ chính xác khi nhận diện trong các điều kiện thực tế khác nhau.
    
    Tham số:
        image (np.ndarray): Ảnh gốc chưa cắt (full image) định dạng BGR.
        process_face_fn (Callable): Hàm xử lý trích xuất đặc trưng khuôn mặt (ví dụ: `process_frame_sync`).
        n_geometric (int): Số lượng ảnh biến đổi hình học (xoay, lật, phối cảnh) cần tạo (mặc định là 7).
        n_photo (int): Số lượng ảnh biến đổi ánh sáng (chỉnh sáng/tương phản/nhiễu/mờ) cần tạo (mặc định là 5).
        n_combined (int): Số lượng ảnh kết hợp đồng thời hình học và ánh sáng cần tạo (mặc định là 2).
        n_occlusion (int): Số lượng ảnh giả lập đeo kính hoặc che mặt cần tạo (mặc định là 2).
        
    Trả về:
        List[np.ndarray]: Danh sách các vector đặc trưng hợp lệ (gồm vector ảnh gốc và các biến thể tăng cường đã qua bộ lọc).
    """
    embeddings = []
    det_score_threshold = 0.50  # Ngưỡng tin cậy tối thiểu của InsightFace để chấp nhận khuôn mặt phát hiện được

    # 1. Trích xuất vector đặc trưng từ ảnh gốc trước tiên
    try:
        faces = process_face_fn(image)
        if faces and len(faces) > 0:
            embedding = faces[0].get("embedding")
            det_score = faces[0].get("det_score", 0)
            if embedding is not None and det_score >= det_score_threshold:
                embeddings.append(embedding)
    except Exception as e:
        pass

    # Nếu không phát hiện được khuôn mặt ở ảnh gốc thì dừng luôn
    if not embeddings:
        return []

    # Danh sách cấu hình tăng cường: liên kết từng pipeline tăng cường với số lượng cần tạo
    configs = [
        (GEO_AUG, n_geometric),
        (PHOTO_AUG, n_photo),
        (COMBINED_AUG, n_combined),
        (OCC_AUG, n_occlusion),
    ]

    # 2. Vòng lặp áp dụng các phương pháp tăng cường hình ảnh
    for aug_pipeline, target_count in configs:
        attempts = 0
        max_attempts = target_count * 3  # Số lần thử tối đa để tránh lặp vô hạn nếu ảnh bị lỗi nhiều
        added = 0

        while added < target_count and attempts < max_attempts:
            attempts += 1
            try:
                # Thực hiện tăng cường ảnh
                aug_result = aug_pipeline(image=image)
                aug_img = aug_result["image"]

                # Phát hiện khuôn mặt và trích xuất vector đặc trưng từ ảnh đã tăng cường
                faces = process_face_fn(aug_img)
                if faces and len(faces) > 0:
                    embedding = faces[0].get("embedding")
                    det_score = faces[0].get("det_score", 0)
                    # Chỉ thêm vector nếu độ tin cậy phát hiện khuôn mặt đạt ngưỡng
                    if embedding is not None and det_score >= det_score_threshold:
                        embeddings.append(embedding)
                        added += 1
            except Exception:
                continue

    # 3. Lọc bỏ các vector quá giống nhau hoặc quá sai lệch so với ảnh gốc
    if embeddings:
        filtered = filter_embeddings(embeddings, min_similarity=0.35, max_similarity=0.99)
        return filtered if filtered else [embeddings[0]]  # Trả về tối thiểu ảnh gốc nếu lọc hết
    return embeddings


def assess_enrollment_quality(
    bgr: np.ndarray,
    faces: list,
    face_crop: np.ndarray,
) -> dict:
    """
    Đánh giá chất lượng toàn diện của ảnh đăng ký (được chụp hoặc tải lên từ thẻ).
    Đảm bảo ảnh đăng ký đạt chất lượng tiêu chuẩn để tránh lỗi nhận diện sau này.
    
    Tham số:
        bgr (np.ndarray): Ảnh gốc đầy đủ định dạng BGR.
        faces (list): Kết quả phát hiện khuôn mặt từ InsightFace.
        face_crop (np.ndarray): Ảnh khuôn mặt đã cắt (crop).
        
    Trả về:
        dict: Chứa:
            - ok (bool): Ảnh đạt tiêu chuẩn đăng ký hay không.
            - reasons (list[str]): Danh sách các lỗi nếu có (ví dụ: ảnh mờ, tối, mặt nhỏ,...).
            - blur_score (float): Điểm sắc nét thực tế.
            - contrast (float): Điểm tương phản thực tế.
            - brightness (float): Điểm độ sáng thực tế.
    """
    target_img = bgr
    # Nếu phát hiện khuôn mặt, chúng ta sẽ cắt chính xác vùng khuôn mặt để đánh giá chất lượng thay vì đánh giá toàn ảnh
    if faces:
        h, w = bgr.shape[:2]
        bbox = faces[0]["bbox"]
        x1 = max(0, int(bbox[0]))
        y1 = max(0, int(bbox[1]))
        x2 = min(w, int(bbox[2]))
        y2 = min(h, int(bbox[3]))
        if (x2 - x1) > 10 and (y2 - y1) > 10:
            target_img = bgr[y1:y2, x1:x2]

    # Đánh giá độ sắc nét, tương phản, độ sáng trên vùng khuôn mặt
    quality = assess_image_quality(target_img)
    reasons = []

    # Ngưỡng chất lượng thiết lập riêng cho việc đăng ký khuôn mặt:
    if quality["blur_score"] <= 8:
        reasons.append("Ảnh bị mờ (Độ sắc nét quá thấp)")
    if quality["contrast"] <= 5:
        reasons.append("Độ tương phản của ảnh quá thấp")
    if quality["brightness"] < 25 or quality["brightness"] > 235:
        reasons.append("Độ sáng của ảnh nằm ngoài phạm vi cho phép")

    # Kiểm tra kích thước hộp bao khuôn mặt tối thiểu phải đạt 60px
    if faces:
        face = faces[0]
        if not validate_face_size(face["bbox"], face["frame_shape"], min_px=60):
            reasons.append("Khuôn mặt quá nhỏ (phải lớn hơn 60px)")

    return {
        "ok": len(reasons) == 0,
        "reasons": reasons,
        "blur_score": quality["blur_score"],
        "contrast": quality["contrast"],
        "brightness": quality["brightness"],
    }

