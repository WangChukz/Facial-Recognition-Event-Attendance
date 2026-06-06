import os
import sys
import numpy as np

# PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from app.services.student_classifier import StudentClassifierService

service = StudentClassifierService()
print(f"Model loaded: {service.model is not None}")
print(f"Label map keys count: {len(service.label_map) if service.label_map else 0}")

# Tao 1 vector ngau nhien 512-D
dummy_emb = np.random.rand(512).astype(np.float32)
res = service.predict(dummy_emb, threshold=0.0)
print(f"Predict result with threshold=0.0: {res}")
