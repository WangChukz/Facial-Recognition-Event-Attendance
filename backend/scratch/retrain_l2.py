import os
import sys
import numpy as np
import joblib
from sklearn.svm import SVC
import faiss

# PYTHONPATH setup
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

split_path = os.path.join(backend_dir, "app", "models", "dataset_split.npz")
model_out = os.path.join(backend_dir, "app", "models", "student_svm_classifier.pkl")

if not os.path.exists(split_path):
    print("Error: dataset_split.npz not found.")
    sys.exit(1)

data = np.load(split_path)
X_train = data["X_train"].copy()  # dung copy de tranh readonly views
y_train = data["y_train"]

# Chuan hoa L2 cho X_train
faiss.normalize_L2(X_train)

print(f"Retraining SVM on {X_train.shape[0]} samples with L2 normalization...")
svm_model = SVC(kernel='rbf', C=2.0, gamma='scale', probability=True, random_state=42)
svm_model.fit(X_train, y_train)

# Luu de model moi
joblib.dump(svm_model, model_out)
print("Successfully retrained and saved L2-normalized SVM model!")
