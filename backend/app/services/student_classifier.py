# app/services/student_classifier.py
# Khởi tạo dịch vụ nhận diện sử dụng lớp SVMFaceClassifier mới từ AI Core

import os
import logging
from typing import Dict, Any
import numpy as np
from app.ai_core.classifiers.svm_matcher import SVMFaceClassifier

logger = logging.getLogger("StudentClassifier")

class StudentClassifierService:
    """
    Dịch vụ để nhận diện Sinh viên Học viện Ngân hàng sử dụng mô hình SVM Classifier.
    Lớp này kế thừa và đóng vai trò wrapper cho SVMFaceClassifier chuẩn OOP.
    """
    
    def __init__(self) -> None:
        # Đường dẫn mặc định đến mô hình và nhãn mã hóa
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(os.path.dirname(current_dir), "models", "student_svm_classifier.pkl")
        label_path = os.path.join(os.path.dirname(current_dir), "models", "label_encoder.json")
        
        self.classifier = SVMFaceClassifier(model_path=model_path, label_path=label_path)
        self.load_model()
        
    def load_model(self) -> None:
        """Tải mô hình SVM và mã hóa nhãn từ đĩa vào bộ nhớ RAM."""
        self.classifier.load_model()
        # Duy trì các tham chiếu cũ để tương thích với kiểm thử A/B
        self.model = self.classifier.model
        self.label_map = self.classifier.label_map

    def predict(self, embedding: np.ndarray, threshold: float = 0.75) -> Dict[str, Any]:
        """
        Nhận dạng danh tính sinh viên từ một vector đặc trưng 512 chiều.
        """
        return self.classifier.predict(embedding, threshold)
