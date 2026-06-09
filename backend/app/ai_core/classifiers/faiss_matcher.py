import os
import json
import logging
from typing import Dict, Any, List
import faiss
import numpy as np
from app.ai_core.classifiers.base_classifier import BaseFaceClassifier

logger = logging.getLogger("FaissFaceClassifier")

class FaissFaceClassifier(BaseFaceClassifier):
    """Bộ phân loại sử dụng chỉ mục FAISS để so khớp khuôn mặt."""

    def __init__(self, index_path: str = None, meta_path: str = None, label_map_path: str = None):
        self.index_path = index_path
        self.meta_path = meta_path
        self.label_map_path = label_map_path
        self.index = None
        self.meta = {}
        self.label_map = {}

    def load_model(self) -> None:
        """Tải cơ sở dữ liệu FAISS từ ổ đĩa."""
        try:
            if self.index_path and os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
            if self.meta_path and os.path.exists(self.meta_path):
                with open(self.meta_path, 'r', encoding='utf-8') as f:
                    # Tải hàng lưu trữ thông tin meta
                    self.meta = {int(k): v for k, v in json.load(f).get("rows", {}).items()}
            if self.label_map_path and os.path.exists(self.label_map_path):
                with open(self.label_map_path, 'r', encoding='utf-8') as f:
                    self.label_map = {int(k): v for k, v in json.load(f).items()}
            logger.info("Đã nạp chỉ mục FAISS thành công.")
        except Exception as e:
            logger.error(f"Lỗi khi nạp mô hình FAISS: {str(e)}")

    def predict(self, embedding: np.ndarray, threshold: float = 0.45) -> Dict[str, Any]:
        if self.index is None or not self.meta:
            return {
                "status": "error",
                "student_code": None,
                "student_name": "Lỗi: Chỉ mục FAISS chưa được tải",
                "confidence": 0.0
            }

        try:
            # Chuẩn hóa L2 vector truy vấn
            vec = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
            faiss.normalize_L2(vec)

            # Tìm kiếm lân cận gần nhất (Top-1)
            sims, ids = self.index.search(vec, 1)
            confidence = float(sims[0][0])
            best_fid = int(ids[0][0])

            if best_fid != -1 and confidence >= threshold:
                meta_row = self.meta.get(best_fid)
                if meta_row:
                    user_uuid_str = meta_row.get("user_id")
                    
                    student_info = None
                    for k, info in self.label_map.items():
                        if isinstance(info, dict):
                            # So khớp theo student_id hoặc folder_name hoặc clean_name
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

            return {
                "status": "unknown",
                "student_code": None,
                "student_name": "Người lạ / Chưa đăng ký",
                "confidence": confidence
            }
        except Exception as e:
            logger.error(f"Lỗi truy vấn FAISS: {str(e)}")
            return {
                "status": "error",
                "student_code": None,
                "student_name": "Lỗi xử lý nhận diện",
                "confidence": 0.0
            }
