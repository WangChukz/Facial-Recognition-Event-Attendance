import numpy as np
from typing import Dict, Any, List
from app.ai_core.classifiers.base_classifier import BaseFaceClassifier

class CosineFaceMatcher(BaseFaceClassifier):
    """Bộ phân loại so khớp Cosine Similarity trực tiếp."""

    def __init__(self, registered_embeddings: np.ndarray = None, labels: List[int] = None, label_map: Dict[int, str] = None):
        self.registered_embeddings = registered_embeddings
        self.labels = labels
        self.label_map = label_map

    def load_model(self) -> None:
        """Với Cosine Matcher, dữ liệu mẫu được nạp trực tiếp qua constructor hoặc RAM database."""
        if self.registered_embeddings is not None:
            # Chuẩn hóa L2 trước khi lưu vào bộ nhớ để tính toán nhanh hơn
            norms = np.linalg.norm(self.registered_embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1.0  # Tránh lỗi chia cho 0
            self.registered_embeddings = self.registered_embeddings / norms

    def predict(self, embedding: np.ndarray, threshold: float = 0.45) -> Dict[str, Any]:
        if self.registered_embeddings is None or self.labels is None or self.label_map is None:
            return {
                "status": "error",
                "student_code": None,
                "student_name": "Lỗi: Cơ sở dữ liệu mẫu trống",
                "confidence": 0.0
            }

        try:
            # Đảm bảo vector đầu vào là 1D
            q = np.asarray(embedding, dtype=np.float32).flatten()
            norm_q = np.linalg.norm(q)
            if norm_q > 0:
                q = q / norm_q

            # Tính tích vô hướng giữa query vector và database
            similarities = np.dot(self.registered_embeddings, q)
            best_idx = int(np.argmax(similarities))
            confidence = float(similarities[best_idx])

            if confidence >= threshold:
                best_label = int(self.labels[best_idx])
                student_info = self.label_map.get(best_label)

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
            else:
                return {
                    "status": "unknown",
                    "student_code": None,
                    "student_name": "Người lạ / Chưa đăng ký",
                    "confidence": confidence
                }
        except Exception as e:
            return {
                "status": "error",
                "student_code": None,
                "student_name": f"Lỗi trong quá trình so khớp Cosine: {str(e)}",
                "confidence": 0.0
            }
