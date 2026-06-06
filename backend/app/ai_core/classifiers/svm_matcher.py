import os
import json
import logging
from typing import Dict, Any
import numpy as np
import joblib
import faiss
from app.ai_core.classifiers.base_classifier import BaseFaceClassifier

logger = logging.getLogger("SVMFaceClassifier")

class SVMFaceClassifier(BaseFaceClassifier):
    """Bộ phân loại Support Vector Machine (SVM) phi tuyến (RBF Kernel)."""

    def __init__(self, model_path: str = None, label_path: str = None):
        self.model_path = model_path
        self.label_path = label_path
        self.model = None
        self.label_map = None

    def load_model(self) -> None:
        """Tải tệp Pickle của SVM và tệp nhãn JSON."""
        try:
            if self.model_path and os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            if self.label_path and os.path.exists(self.label_path):
                with open(self.label_path, 'r', encoding='utf-8') as f:
                    self.label_map = {int(k): v for k, v in json.load(f).items()}
            logger.info("Đã tải SVM Classifier thành công.")
        except Exception as e:
            logger.error(f"Lỗi khi tải mô hình SVM: {str(e)}")

    def predict(self, embedding: np.ndarray, threshold: float = 0.15) -> Dict[str, Any]:
        if self.model is None or self.label_map is None:
            return {
                "status": "error",
                "student_code": None,
                "student_name": "Lỗi: Mô hình SVM chưa được tải",
                "confidence": 0.0
            }

        try:
            # Đưa vector về dạng 2D
            x_input = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
            # Chuẩn hóa L2 vector đặc trưng
            faiss.normalize_L2(x_input)

            # Tính xác suất cho tất cả các sinh viên
            probabilities = self.model.predict_proba(x_input)[0]
            best_idx = int(np.argmax(probabilities))
            confidence = float(probabilities[best_idx])

            if confidence >= threshold:
                best_class_label = int(self.model.classes_[best_idx])
                student_info = self.label_map.get(best_class_label)

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
                        # Fallback cho dạng chuỗi cũ
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
            logger.error(f"Lỗi khi dự đoán bằng SVM: {str(e)}")
            return {
                "status": "error",
                "student_code": None,
                "student_name": "Lỗi xử lý nhận diện",
                "confidence": 0.0
            }
