import cv2
import numpy as np
import albumentations as A
from typing import List

def build_geometric_aug() -> A.Compose:
    """
    Xây dựng pipeline tăng cường dữ liệu hình học (Geometric Augmentation) để giả lập các góc quay khuôn mặt, 
    khoảng cách camera và hướng chụp khác nhau.
    
    Các tham số biến đổi:
        - A.Rotate(limit=(-20, 20)): Xoay ngẫu nhiên từ -20 đến 20 độ để giả lập tư thế nghiêng đầu.
        - A.HorizontalFlip(p=0.5): Lật ảnh theo chiều ngang với xác suất 50% để nhân đôi số góc nhìn đối xứng.
        - A.Perspective(scale=(0.02, 0.06)): Biến đổi phối cảnh nhẹ để mô phỏng sự thay đổi độ cao/góc đặt camera.
        - A.ShiftScaleRotate: Tịnh tiến, phóng to/thu nhỏ ngẫu nhiên để giả lập sự thay đổi khoảng cách từ người đến camera.
    """
    return A.Compose([
        A.Rotate(limit=(-20, 20), border_mode=cv2.BORDER_REPLICATE, p=1.0),
        A.HorizontalFlip(p=0.5),
        # A.Perspective: Biến đổi phối cảnh (3D perspective) để mô phỏng việc lệch góc chụp camera
        # - scale=(0.02, 0.06): Phạm vi biến dạng phối cảnh (mức độ xiêu vẹo của hình ảnh, từ 2% đến 6%)
        # - p=0.7: Xác suất (probability) áp dụng phép biến đổi này là 70%
        A.Perspective(scale=(0.02, 0.06), p=0.7),
        # A.ShiftScaleRotate: Tịnh tiến (dịch chuyển), co giãn (thu phóng) và xoay ảnh đồng thời
        # - shift_limit=0.08: Giới hạn dịch chuyển ảnh theo trục X và Y (tối đa 8% kích thước ảnh)
        # - scale_limit=(-0.1, 0.2): Giới hạn thu phóng ảnh (thu nhỏ tối đa 10% hoặc phóng to tối đa 20%)
        # - rotate_limit=0: Giới hạn xoay ở đây đặt là 0 vì đã dùng hàm A.Rotate riêng ở trên
        # - border_mode=cv2.BORDER_REPLICATE: Cách xử lý vùng biên trống sau khi dịch chuyển/thu phóng (sao chép pixel ở biên gần nhất để lấp đầy)
        # - p=0.8: Xác suất áp dụng phép biến đổi này là 80%
        A.ShiftScaleRotate(
            shift_limit=0.08, scale_limit=(-0.1, 0.2),
            rotate_limit=0, border_mode=cv2.BORDER_REPLICATE, p=0.8
        ),
    ])

def build_photometric_aug() -> A.Compose:
    """
    Xây dựng pipeline tăng cường dữ liệu ánh sáng và độ sắc nét (Photometric Augmentation)
    để giả lập các điều kiện môi trường ánh sáng thực tế phức tạp (chói sáng, thiếu sáng, nhiễu cảm biến webcam).
    
    Các tham số biến đổi:
        - RandomBrightnessContrast (p=1.0): Thay đổi ngẫu nhiên độ sáng và độ tương phản (lên tới 35%).
        - RandomGamma (p=1.0): Biến đổi gamma để chỉnh sáng phi tuyến tính.
        - CLAHE (p=1.0): Áp dụng CLAHE ngẫu nhiên để giả lập cân bằng sáng cục bộ.
        - GaussNoise / ISONoise (p=0.6): Thêm nhiễu hạt để giả lập camera chất lượng thấp hoặc thiếu sáng bị nhiễu hạt.
        - MotionBlur / GaussianBlur (p=0.4): Làm mờ chuyển động hoặc làm mờ do lệch tiêu cự (out-of-focus).
        - HueSaturationValue (p=0.5): Thay đổi hệ màu HSV nhẹ để cân bằng trắng sai lệch từ camera.
    """
    return A.Compose([
        # A.OneOf: Chỉ chọn 1 trong các phép biến đổi con bên trong để áp dụng (ở đây có xác suất áp dụng nhóm này là 90% [p=0.9])
        A.OneOf([
            # A.RandomBrightnessContrast: Thay đổi ngẫu nhiên độ sáng và độ tương phản
            # - brightness_limit=0.35: Giới hạn thay đổi độ sáng (từ -35% đến +35%)
            # - contrast_limit=0.35: Giới hạn thay đổi độ tương phản (từ -35% đến +35%)
            # - p=1.0: Xác suất áp dụng của phép biến đổi này (nếu nhóm OneOf được chọn) là 100%
            A.RandomBrightnessContrast(brightness_limit=0.35, contrast_limit=0.35, p=1.0),
            # A.RandomGamma: Thay đổi hệ số Gamma để mô phỏng ánh sáng phi tuyến tính
            # - gamma_limit=(60, 140): Khoảng điều chỉnh gamma (từ 0.6 đến 1.4, trong đó 100 tương ứng 1.0)
            # - p=1.0: Xác suất áp dụng là 100%
            A.RandomGamma(gamma_limit=(60, 140), p=1.0),
            # A.CLAHE: Cân bằng biểu đồ xám cục bộ
            # - clip_limit=(1.0, 4.0): Khoảng giới hạn độ tương phản cục bộ ngẫu nhiên (từ 1.0 đến 4.0)
            # - tile_grid_size=(4, 4): Lưới phân vùng ảnh để tính toán cục bộ (chia ảnh thành lưới 4x4 ô)
            # - p=1.0: Xác suất áp dụng là 100%
            A.CLAHE(clip_limit=(1.0, 4.0), tile_grid_size=(4, 4), p=1.0),
        ], p=0.9),
        # A.OneOf: Chọn 1 phép thêm nhiễu ngẫu nhiên với xác suất nhóm là 60% (p=0.6) để giả lập camera bị nhiễu hạt
        A.OneOf([
            # A.GaussNoise: Thêm nhiễu Gaussian (nhiễu hạt trắng thông thường)
            # - var_limit=(5.0, 30.0): Phương sai của nhiễu (nhiễu nhẹ đến trung bình)
            # - p=1.0: Xác suất áp dụng là 100%
            A.GaussNoise(var_limit=(5.0, 30.0), p=1.0),
            # A.ISONoise: Thêm nhiễu hạt ISO (giả lập nhiễu cảm biến máy ảnh khi chụp tối)
            # - color_shift=(0.01, 0.05): Mức độ sai lệch màu sắc hạt nhiễu (từ 1% đến 5%)
            # - p=1.0: Xác suất áp dụng là 100%
            A.ISONoise(color_shift=(0.01, 0.05), p=1.0),
        ], p=0.6),
        # A.OneOf: Chọn 1 phép làm mờ ngẫu nhiên với xác suất nhóm là 40% (p=0.4) để giả lập chuyển động hoặc sai tiêu cự
        A.OneOf([
            # A.MotionBlur: Làm mờ do chuyển động
            # - blur_limit=5: Kích thước nhân làm mờ tối đa (giá trị 5 tương đương bán kính mờ nhỏ)
            # - p=1.0: Xác suất áp dụng là 100%
            A.MotionBlur(blur_limit=5, p=1.0),
            # A.GaussianBlur: Làm mờ Gaussian (mờ đều ảnh)
            # - blur_limit=(3, 5): Kích thước nhân làm mờ ngẫu nhiên từ 3x3 đến 5x5
            # - p=1.0: Xác suất áp dụng là 100%
            A.GaussianBlur(blur_limit=(3, 5), p=1.0),
        ], p=0.4),
        # A.HueSaturationValue: Thay đổi màu sắc, độ bão hòa màu và độ sáng theo không gian màu HSV
        # - hue_shift_limit=8: Giới hạn dịch chuyển sắc độ (màu sắc lệch tông nhẹ)
        # - sat_shift_limit=20: Giới hạn tăng/giảm độ rực màu (20 đơn vị)
        # - val_shift_limit=20: Giới hạn tăng/giảm độ sáng giá trị màu (20 đơn vị)
        # - p=0.5: Xác suất áp dụng biến đổi HSV này là 50%
        A.HueSaturationValue(
            hue_shift_limit=8, sat_shift_limit=20, val_shift_limit=20, p=0.5
        ),
    ])

def build_occlusion_aug() -> A.Compose:
    """
    Xây dựng pipeline giả lập vật cản che khuất khuôn mặt (Occlusion Augmentation).
    Sử dụng CoarseDropout để che đi các vùng ngẫu nhiên trên ảnh nhằm giả lập trường hợp đeo kính, đeo khẩu trang,
    hoặc tóc che khuất một phần mặt.
    
    Các tham số:
        - max_holes=3: Số lỗ che tối đa là 3.
        - max_height/width=30: Kích thước vùng che tối đa 30x30 pixel.
        - p=0.4: Xác suất áp dụng là 40%.
    """
    return A.Compose([
        A.CoarseDropout(
            max_holes=3, max_height=30, max_width=30,
            min_holes=1, min_height=10, min_width=10,
            fill_value=0, p=0.4
        ),
    ])

def build_combined_aug() -> A.Compose:
    """
    Xây dựng pipeline tăng cường kết hợp đồng thời cả biến đổi hình học (Geometric) và ánh sáng (Photometric)
    để mô phỏng các trường hợp khó nhất (ví dụ vừa nghiêng đầu vừa bị ngược sáng mạnh).
    """
    return A.Compose([
        build_photometric_aug(),
        build_geometric_aug(),
    ])

# Các đối tượng Pipeline tăng cường được khởi tạo sẵn để sử dụng trong dự án
GEO_AUG = build_geometric_aug()
PHOTO_AUG = build_photometric_aug()
OCC_AUG = build_occlusion_aug()
COMBINED_AUG = build_combined_aug()

def assess_image_quality(bgr: np.ndarray) -> dict:
    """
    Đánh giá chất lượng ảnh đầu vào bằng các phép đo trực quan để loại bỏ các ảnh quá mờ,
    quá tối hoặc quá sáng trước khi đăng ký.
    
    Tham số:
        bgr (np.ndarray): Ảnh đầu vào định dạng BGR.
        
    Trả về:
        dict: Chứa các điểm số chất lượng bao gồm:
            - blur_score (float): Điểm độ mờ (phương sai toán tử Laplacian). Điểm càng cao ảnh càng sắc nét.
            - brightness (float): Độ sáng trung bình (0 - 255).
            - contrast (float): Độ tương phản (độ lệch chuẩn độ xám).
            - ok (bool): Kết quả đánh giá chung đạt chất lượng hay không dựa trên các ngưỡng định sẵn.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = bgr.shape[:2]

    # Tính toán độ mờ bằng phương sai Laplacian
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    # Tính độ sáng trung bình của ảnh xám
    mean_brightness = gray.mean()
    # Tính độ tương phản bằng độ lệch chuẩn
    contrast = gray.std()

    # Ngưỡng chất lượng tối thiểu:
    # - blur_score > 15: Đủ sắc nét (không quá mờ)
    # - contrast > 10: Độ tương phản đủ tốt để phân biệt chi tiết
    # - 40 < mean_brightness < 220: Không bị quá tối hoặc quá sáng cháy hình
    return {
        'blur_score': blur_score,
        'brightness': mean_brightness,
        'contrast': contrast,
        'ok': blur_score > 15 and contrast > 10 and mean_brightness > 40 and mean_brightness < 220,
    }

def crop_face_with_margin(bgr: np.ndarray, bbox: list, margin: float = 0.25) -> np.ndarray:
    """
    Cắt vùng khuôn mặt ra khỏi bức ảnh gốc kèm theo một tỷ lệ lề xung quanh khuôn mặt (margin),
    sau đó chuẩn hóa kích thước về 256x256 pixel bằng phép nội suy Lanczos.
    Tỷ lệ margin giúp bộ tăng cường (xoay, dịch chuyển) không làm mất các chi tiết rìa tóc/tai của khuôn mặt.
    
    Tham số:
        bgr (np.ndarray): Ảnh gốc đầu vào định dạng BGR.
        bbox (list): Tọa độ hộp bao khuôn mặt dạng [x1, y1, x2, y2].
        margin (float): Tỷ lệ lề mở rộng xung quanh hộp bao (mặc định mở rộng thêm 25% chiều rộng và chiều cao).
        
    Trả về:
        np.ndarray: Khuôn mặt đã cắt và thu phóng về kích thước chuẩn hóa 256x256.
    """
    x1, y1, x2, y2 = [int(v) for v in bbox]
    face_w, face_h = x2 - x1, y2 - y1

    # Tính toán khoảng cách lề
    mx = int(face_w * margin)
    my = int(face_h * margin)

    # Đảm bảo tọa độ cắt không vượt quá biên giới hạn của bức ảnh gốc
    h, w = bgr.shape[:2]
    x1c = max(0, x1 - mx)
    y1c = max(0, y1 - my)
    x2c = min(w, x2 + mx)
    y2c = min(h, y2 + my)

    face_crop = bgr[y1c:y2c, x1c:x2c]
    # Resize về 256x256 bằng thuật toán nội suy INTER_LANCZOS4 để giữ độ sắc nét cao nhất
    return cv2.resize(face_crop, (256, 256), interpolation=cv2.INTER_LANCZOS4)

def validate_face_size(bbox: list, img_shape: tuple, min_px: int = 80) -> bool:
    """
    Xác thực xem kích thước của khuôn mặt được phát hiện có đạt kích thước tối thiểu yêu cầu hay không.
    Giúp lọc các khuôn mặt ở quá xa camera dẫn tới đặc trưng trích xuất bị nhiễu.
    
    Tham số:
        bbox (list): Tọa độ hộp bao khuôn mặt [x1, y1, x2, y2].
        img_shape (tuple): Kích thước ảnh gốc (được truyền vào nhưng không dùng trực tiếp trong hàm).
        min_px (int): Ngưỡng kích thước chiều rộng/chiều cao tối thiểu tính bằng pixel (mặc định là 80px).
        
    Trả về:
        bool: True nếu khuôn mặt đủ lớn, False nếu quá nhỏ.
    """
    x1, y1, x2, y2 = bbox
    face_w, face_h = x2 - x1, y2 - y1
    return face_w >= min_px and face_h >= min_px

def filter_embeddings(
    embeddings: List[np.ndarray],
    min_similarity: float = 0.35,
    max_similarity: float = 0.99,
) -> List[np.ndarray]:
    """
    Bộ lọc giúp loại bỏ các vector đặc trưng (embeddings) bị lỗi hoặc quá giống nhau được sinh ra từ ảnh tăng cường.
    - Loại bỏ các vector có độ tương đồng cosine quá thấp (< min_similarity) so với ảnh gốc (do biến đổi làm biến dạng khuôn mặt quá nhiều).
    - Loại bỏ các vector quá giống nhau (> max_similarity) để tiết kiệm không gian lưu trữ và tránh overfitting trong FAISS.
    
    Tham số:
        embeddings (List[np.ndarray]): Danh sách các vector đặc trưng khuôn mặt (vector đầu tiên embeddings[0] phải là ảnh gốc).
        min_similarity (float): Ngưỡng tương đồng cosine tối thiểu (mặc định 0.35).
        max_similarity (float): Ngưỡng tương đồng cosine tối đa (mặc định 0.99).
        
    Trả về:
        List[np.ndarray]: Danh sách các vector đặc trưng đã được chọn lọc (luôn giữ lại vector ảnh gốc đầu tiên).
    """
    if not embeddings:
        return []

    orig = np.asarray(embeddings[0], dtype=np.float32).reshape(-1)
    orig_norm = np.linalg.norm(orig)
    if orig_norm > 0:
        orig = orig / orig_norm
    filtered = [embeddings[0]]

    for emb in embeddings[1:]:
        candidate = np.asarray(emb, dtype=np.float32).reshape(-1)
        candidate_norm = np.linalg.norm(candidate)
        if candidate_norm > 0:
            candidate = candidate / candidate_norm
        # Tính tương đồng Cosine (tích vô hướng của 2 vector đã chuẩn hóa)
        sim = float(np.dot(orig, candidate))
        if min_similarity <= sim <= max_similarity:
            filtered.append(emb)

    return filtered

def calibrate_threshold(
    same_user_scores: List[float],
    diff_user_scores: List[float],
) -> tuple[float, float]:
    """
    Tự động hiệu chuẩn để tìm ra ngưỡng tương đồng (threshold) tối ưu nhất dựa trên dữ liệu thử nghiệm thực tế.
    
    Tham số:
        same_user_scores (List[float]): Danh sách điểm tương đồng của cùng một người (chính xác).
        diff_user_scores (List[float]): Danh sách điểm tương đồng giữa các người khác nhau (sai lệch).
        
    Trả về:
        tuple[float, float]: (Ngưỡng tối ưu tìm được, Độ chính xác cao nhất đạt được tại ngưỡng đó).
    """
    thresholds = np.arange(0.3, 0.8, 0.01)
    best_threshold, best_accuracy = 0, 0

    for threshold in thresholds:
        tp = sum(1 for s in same_user_scores if s >= threshold)
        fn = sum(1 for s in same_user_scores if s < threshold)
        tn = sum(1 for s in diff_user_scores if s < threshold)
        fp = sum(1 for s in diff_user_scores if s >= threshold)

        total = tp + tn + fp + fn
        accuracy = (tp + tn) / total if total > 0 else 0

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = threshold

    return best_threshold, best_accuracy

