import cv2
import numpy as np

def apply_clahe(bgr: np.ndarray) -> np.ndarray:
    """
    Áp dụng thuật toán CLAHE (Cân bằng lược đồ xám thích ứng giới hạn độ tương phản) với clipLimit cố định.
    
    Tham số:
        bgr (np.ndarray): Ảnh đầu vào định dạng BGR (OpenCV mặc định).
        
    Trả về:
        np.ndarray: Ảnh đã được tăng cường độ tương phản cục bộ định dạng BGR.
    """
    # Chuyển từ không gian màu BGR sang LAB để xử lý độ sáng độc lập với màu sắc
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Khởi tạo CLAHE với giới hạn độ tương phản cố định là 2.5
    # tileGridSize=(8, 8): Chia bức ảnh thành lưới 8x8 ô để tính toán cục bộ
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    
    # Gộp lại và chuyển về không gian màu BGR ban đầu
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

def apply_adaptive_clahe(bgr: np.ndarray) -> np.ndarray:
    """
    Áp dụng CLAHE thích ứng dựa trên độ sáng trung bình thực tế của ảnh,
    giúp tự động xử lý ảnh ngược sáng, quá sáng (chói đèn) hoặc quá tối (trong phòng/hội trường).
    Sau đó áp dụng thêm bộ lọc làm sắc nét nhẹ để tăng cường đường biên khuôn mặt.
    
    Tham số:
        bgr (np.ndarray): Ảnh đầu vào định dạng BGR.
        
    Trả về:
        np.ndarray: Ảnh sau khi được tiền xử lý tối ưu về ánh sáng và độ sắc nét.
    """
    # Chuyển đổi sang hệ màu LAB
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b_ch = cv2.split(lab)

    # Tính độ sáng trung bình của kênh L (Lightness: 0 - 255)
    mean_l = l.mean()
    
    # Tự động điều chỉnh tham số clipLimit (giới hạn tương phản) thích ứng:
    if mean_l < 80:      # Ảnh tối (thiếu sáng) -> Tăng mạnh độ tương phản để lấy chi tiết tối
        clip = 3.5
    elif mean_l > 180:   # Ảnh quá sáng (chói sáng) -> Giảm độ tương phản để tránh cháy sáng
        clip = 1.5
    else:                # Ánh sáng bình thường
        clip = 2.0

    # Áp dụng CLAHE thích ứng lên kênh độ sáng L
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    cl = clahe.apply(l)

    # Tiền xử lý làm sắc nét biên (Unsharp Masking):
    # Trích xuất chi tiết tần số cao bằng cách lấy ảnh gốc trừ đi ảnh làm mờ Gaussian
    gaussian = cv2.GaussianBlur(cl, (5, 5), 1.0)
    # Công thức: cl_new = cl * 1.3 - gaussian * 0.3
    cl = np.clip(cv2.addWeighted(cl, 1.3, gaussian, -0.3, 0), 0, 255).astype(np.uint8)

    # Gộp lại thành ảnh LAB hoàn chỉnh và chuyển về BGR
    limg = cv2.merge((cl, a, b_ch))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

