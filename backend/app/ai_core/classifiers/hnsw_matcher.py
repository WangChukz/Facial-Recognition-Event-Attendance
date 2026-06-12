import os
import json
import logging
from typing import Dict, Any, List
import faiss
import numpy as np
from app.ai_core.classifiers.base_classifier import BaseFaceClassifier

logger = logging.getLogger("HNSWFaceClassifier")

class HNSWFaceClassifier(BaseFaceClassifier):
    """
    Bộ phân loại khuôn mặt (Classifier) sử dụng cấu trúc đồ thị HNSW để tìm kiếm lân cận gần nhất (Nearest Neighbor).
    Kế thừa từ lớp BaseFaceClassifier để định hình interface chung cho việc nhận diện.
    """

    def __init__(self, index_path: str = None, meta_path: str = None, label_map_path: str = None):
        """
        Khởi tạo bộ phân loại HNSW.

        Tham số:
            index_path (str): Đường dẫn tới tệp chỉ mục HNSW (.index / .bin).
            meta_path (str): Đường dẫn tới tệp siêu dữ liệu JSON chứa vị trí và ID người dùng.
            label_map_path (str): Đường dẫn tới tệp chứa danh sách sinh viên ánh xạ (`label_map.json`).
        """
        self.index_path = index_path
        self.meta_path = meta_path
        self.label_map_path = label_map_path
        self.index = None
        self.position_to_meta = []
        self.label_map = {}

    def load_model(self) -> None:
        """Tải chỉ mục HNSW, file siêu dữ liệu ánh xạ vị trí và label map từ ổ đĩa cứng lên bộ nhớ RAM."""
        try:
            # 1. Tải chỉ mục FAISS HNSW
            if self.index_path and os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
            
            # 2. Tải siêu dữ liệu vị trí tương ứng
            if self.meta_path and os.path.exists(self.meta_path):
                with open(self.meta_path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                    self.position_to_meta = raw.get("position_to_meta", [])
            
            # 3. Tải danh sách ánh xạ nhãn thông tin sinh viên
            if self.label_map_path and os.path.exists(self.label_map_path):
                with open(self.label_map_path, 'r', encoding='utf-8') as f:
                    self.label_map = {int(k): v for k, v in json.load(f).items()}
            logger.info("Đã nạp chỉ mục HNSW thành công.")
        except Exception as e:
            logger.error(f"Lỗi khi nạp mô hình HNSW: {str(e)}")

    def predict(self, embedding: np.ndarray, threshold: float = 0.45) -> Dict[str, Any]:
        """
        Dự đoán danh tính (nhận diện) sinh viên dựa trên vector đặc trưng khuôn mặt đầu vào.
        
        Tham số:
            embedding (np.ndarray): Vector đặc trưng khuôn mặt trích xuất được từ camera (512 chiều).
            threshold (float): Ngưỡng nhận diện (độ tương đồng tối thiểu để coi là khớp, mặc định là 0.45).
            
        Trả về:
            Dict[str, Any]: Kết quả nhận diện gồm:
                - status (str): Trạng thái nhận diện ("known", "unknown", "error").
                - student_code (str/None): Mã số sinh viên của người khớp.
                - student_name (str): Tên hiển thị của người khớp hoặc thông báo lỗi.
                - class_name (str/None): Tên lớp học của sinh viên.
                - confidence (float): Độ tương đồng đo được (0.0 đến 1.0).
        """
        # Kiểm tra xem chỉ mục đã được nạp hay chưa
        if self.index is None or not self.position_to_meta:
            return {
                "status": "error",
                "student_code": None,
                "student_name": "Lỗi: Chỉ mục HNSW chưa được tải",
                "confidence": 0.0
            }

        try:
            # 1. Chuẩn hóa L2 vector truy vấn đầu vào
            vec = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
            faiss.normalize_L2(vec)

            # 2. Tìm kiếm vector khớp nhất (Top-1) trong đồ thị HNSW
            sims, positions = self.index.search(vec, 1)
            confidence = float(sims[0][0])
            best_pos = int(positions[0][0])

            # 3. Đánh giá xem kết quả có hợp lệ và vượt ngưỡng nhận diện tối thiểu hay không
            if best_pos != -1 and confidence >= threshold:
                if 0 <= best_pos < len(self.position_to_meta):
                    meta_row = self.position_to_meta[best_pos]
                    user_uuid_str = meta_row.get("user_id")

                    # 4. Tìm kiếm thông tin sinh viên tương ứng trong label_map
                    student_info = None
                    for k, info in self.label_map.items():
                        if isinstance(info, dict):
                            # So khớp UUID người dùng với folder_name hoặc student_id của sinh viên
                            folder_name = info.get("folder_name", "")
                            student_id = info.get("student_id", "")
                            if (user_uuid_str in folder_name or folder_name in user_uuid_str or
                                    user_uuid_str in student_id or student_id in user_uuid_str):
                                student_info = info
                                break
                        else:
                            if user_uuid_str in str(info) or str(info) in user_uuid_str:
                                student_info = info
                                break

                    # 5. Nếu tìm thấy thông tin sinh viên phù hợp, trả về kết quả
                    if student_info:
                        if isinstance(student_info, dict):
                            return {
                                "status": "known",
                                "student_code": student_info.get("student_id"),
                                "student_name": student_info.get("name"),
                                "class_name": student_info.get("class"),
                                "confidence": confidence
                            }
                        else:
                            parts = str(student_info).split("_")
                            student_code = parts[0]
                            student_name = parts[1] if len(parts) > 1 else str(student_info)
                            return {
                                "status": "known",
                                "student_code": student_code,
                                "student_name": student_name,
                                "confidence": confidence
                            }

            # Trường hợp không khớp hoặc độ tin cậy dưới ngưỡng nhận diện
            return {
                "status": "unknown",
                "student_code": None,
                "student_name": "Người lạ / Chưa đăng ký",
                "confidence": confidence
            }
        except Exception as e:
            logger.error(f"Lỗi truy vấn HNSW: {str(e)}")
            return {
                "status": "error",
                "student_code": None,
                "student_name": "Lỗi xử lý nhận diện",
                "confidence": 0.0
            }

