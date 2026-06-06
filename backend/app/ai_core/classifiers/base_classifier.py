from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np

class BaseFaceClassifier(ABC):
    """Lớp cơ sở trừu tượng định nghĩa giao diện chuẩn cho các Classifier Heads."""

    @abstractmethod
    def load_model(self) -> None:
        """Tải mô hình từ đĩa vào bộ nhớ RAM."""
        pass

    @abstractmethod
    def predict(self, embedding: np.ndarray, threshold: float = 0.5) -> Dict[str, Any]:
        """
        Nhận diện danh tính từ vector embedding 512 chiều.

        Args:
            embedding: Vector đặc trưng 512 chiều (1D numpy array).
            threshold: Ngưỡng nhận diện (độ tin cậy tối thiểu).

        Returns:
            Dict chứa thông tin kết quả dự đoán (status, student_code, student_name, confidence).
        """
        pass
