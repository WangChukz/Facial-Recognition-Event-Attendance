import cv2
import numpy as np

def apply_clahe(bgr: np.ndarray) -> np.ndarray:
    """CLAHE với clipLimit=2.5 cố định."""
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

def apply_adaptive_clahe(bgr: np.ndarray) -> np.ndarray:
    """CLAHE thích ứng dựa trên độ sáng trung bình của ảnh.
    Giúp xử lý các vấn đề ngược sáng, ánh đèn rọi hoặc tối góc tại hội trường."""
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b_ch = cv2.split(lab)

    mean_l = l.mean()
    if mean_l < 80:      # Ảnh tối
        clip = 3.5
    elif mean_l > 180:   # Ảnh quá sáng
        clip = 1.5
    else:                # Ánh sáng bình thường
        clip = 2.0

    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    cl = clahe.apply(l)

    # Làm sắc nét biên nhẹ bằng Gaussian Blur và weighted add
    gaussian = cv2.GaussianBlur(cl, (5, 5), 1.0)
    cl = np.clip(cv2.addWeighted(cl, 1.3, gaussian, -0.3, 0), 0, 255).astype(np.uint8)

    limg = cv2.merge((cl, a, b_ch))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
