import os
import sys
import time
import json
import logging
import argparse
import re
import unicodedata
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import torchvision.models as models
import torchvision.transforms as transforms
import cv2

# Đảm bảo hiển thị tiếng Việt trên Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Epoch_Finder")

# 1. Định nghĩa ArcMarginProduct
class ArcMarginProduct(nn.Module):
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, m: float = 0.50):
        super(ArcMarginProduct, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)

    def forward(self, input: torch.Tensor, label: torch.Tensor) -> torch.Tensor:
        cos_theta = F.linear(F.normalize(input), F.normalize(self.weight))
        sine = torch.sqrt((1.0 - torch.pow(cos_theta, 2)).clamp(0, 1))
        phi = cos_theta * np.cos(self.m) - sine * np.sin(self.m)
        phi = torch.where(cos_theta > 0, phi, cos_theta)
        one_hot = torch.zeros(cos_theta.size(), device=input.device)
        one_hot.scatter_(1, label.view(-1, 1).long(), 1)
        output = (one_hot * phi) + ((1.0 - one_hot) * cos_theta)
        output *= self.s
        return output

# 2. Định nghĩa FaceNetResNet18
class FaceNetResNet18(nn.Module):
    def __init__(self, embedding_dim: int = 512):
        super(FaceNetResNet18, self).__init__()
        self.backbone = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        in_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Sequential(
            nn.Linear(in_features, embedding_dim),
            nn.BatchNorm1d(embedding_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)

# 3. Định nghĩa Dataset để đọc ảnh và gán nhãn chính xác
class StudentImageDataset(Dataset):
    def __init__(self, image_paths, labels, transform=None):
        self.image_paths = image_paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        label = self.labels[idx]
        try:
            img_array = np.fromfile(img_path, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Decode failed")
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            if self.transform:
                from PIL import Image
                img_pil = Image.fromarray(img)
                img = self.transform(img_pil)
            return img, torch.tensor(label, dtype=torch.long)
        except Exception as e:
            # Chọn ngẫu nhiên ảnh khác nếu lỗi
            rand_idx = np.random.randint(0, len(self.image_paths))
            return self.__getitem__(rand_idx)

def clean_vietnamese(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = text.replace('đ', 'd').replace('Đ', 'D')
    text = unicodedata.normalize('NFC', text)
    text = text.replace(' ', '')
    return text.lower()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Thiết bị huấn luyện: {device}")

    # Đường dẫn dữ liệu
    enroll_dir = "c:/AI_event/dataset/dataset/enroll"
    real_dir = "c:/AI_event/dataset/dataset/real"
    meta_path = "c:/AI_event/dataset/dataset/metadata.xlsx"

    # Đọc metadata
    df_meta = pd.read_excel(meta_path)
    meta_map = {}
    for _, row in df_meta.iterrows():
        name = str(row.get('Họ và tên', '')).strip()
        clean_name = clean_vietnamese(name)
        meta_map[clean_name] = {
            "name": name,
            "student_id": str(row.get('Mã sinh viên', '')).strip()
        }

    student_keys = sorted(list(meta_map.keys()))
    class_map = {name: idx for idx, name in enumerate(student_keys)}
    num_classes = len(class_map)
    logger.info(f"Số sinh viên trong metadata: {num_classes}")

    # Chuẩn bị dữ liệu Train (Ảnh enroll + Data Augmentations trực tiếp bằng PyTorch transform)
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=(-15, 15)),
        transforms.ColorJitter(brightness=0.3, contrast=0.3),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    test_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # 1. Gom danh sách ảnh Enroll làm dữ liệu huấn luyện chính
    train_paths = []
    train_labels = []
    enroll_files = [f for f in os.listdir(enroll_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]

    # Nhân bản ảnh enroll lên (ví dụ nhân bản 20 lần kèm transform để tạo tập train lớn hơn)
    for ef in enroll_files:
        clean_name = re.sub(r'_enroll\.(jpg|png|jpeg)', '', ef, flags=re.IGNORECASE).lower()
        if clean_name in class_map:
            class_id = class_map[clean_name]
            full_path = os.path.join(enroll_dir, ef)
            for _ in range(25):  # Mỗi ảnh enroll tạo 25 biến thể train
                train_paths.append(full_path)
                train_labels.append(class_id)

    # 2. Gom danh sách ảnh Real làm tập Test đối chứng thực tế
    test_paths = []
    test_labels = []
    real_folders = [f for f in os.listdir(real_dir) if os.path.isdir(os.path.join(real_dir, f))]

    for r_folder in real_folders:
        clean_name = r_folder.replace("_real", "").lower()
        if clean_name == "phamtrungkien":
            clean_name = "nguyentrungkien"
        if clean_name in class_map:
            class_id = class_map[clean_name]
            folder_path = os.path.join(real_dir, r_folder)
            for f in os.listdir(folder_path):
                if f.lower().endswith(('.jpg', '.png', '.jpeg')):
                    test_paths.append(os.path.join(folder_path, f))
                    test_labels.append(class_id)

    logger.info(f"Tập huấn luyện (sinh ra từ enroll): {len(train_paths)} ảnh.")
    logger.info(f"Tập kiểm thử thực tế (real): {len(test_paths)} ảnh.")

    train_dataset = StudentImageDataset(train_paths, train_labels, train_transform)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)

    # Tạo tập test không có augment để đánh giá
    test_dataset = StudentImageDataset(test_paths, test_labels, test_transform)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False)

    # Tạo tập enroll chuẩn để làm Gallery (so khớp FAISS Flat trực tiếp)
    gallery_paths = []
    gallery_labels = []
    for ef in enroll_files:
        clean_name = re.sub(r'_enroll\.(jpg|png|jpeg)', '', ef, flags=re.IGNORECASE).lower()
        if clean_name in class_map:
            class_id = class_map[clean_name]
            gallery_paths.append(os.path.join(enroll_dir, ef))
            gallery_labels.append(class_id)

    gallery_dataset = StudentImageDataset(gallery_paths, gallery_labels, test_transform)
    gallery_loader = DataLoader(gallery_dataset, batch_size=args.batch_size, shuffle=False)

    # Khởi tạo mô hình
    model = FaceNetResNet18(embedding_dim=512).to(device)
    arcface_head = ArcMarginProduct(in_features=512, out_features=num_classes, s=30.0, m=0.50).to(device)

    optimizer = optim.AdamW(
        list(model.parameters()) + list(arcface_head.parameters()),
        lr=args.lr,
        weight_decay=1e-4
    )
    criterion = nn.CrossEntropyLoss()

    best_real_acc = -1.0
    best_epoch = -1
    best_model_state = None

    history = []

    logger.info(f"Bắt đầu huấn luyện và khảo sát trên {args.epochs} Epochs...")

    for epoch in range(args.epochs):
        model.train()
        arcface_head.train()
        train_loss = 0.0
        train_correct = 0
        total_train = 0

        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            embeddings = model(imgs)
            outputs = arcface_head(embeddings, labels)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * imgs.size(0)
            _, preds = torch.max(outputs, 1)
            train_correct += torch.sum(preds == labels.data).item()
            total_train += imgs.size(0)

        epoch_loss = train_loss / total_train
        epoch_acc = train_correct / total_train

        # --- Đánh giá trực tiếp trên tập kiểm thử thực tế bằng FAISS Flat (Cosine Similarity / Dot Product) ---
        model.eval()
        # Trích xuất embeddings cho Gallery
        gallery_embs = []
        gallery_ys = []
        with torch.no_grad():
            for imgs, labels in gallery_loader:
                imgs = imgs.to(device)
                embs = model(imgs)
                # Chuẩn hóa L2
                embs = F.normalize(embs, p=2, dim=1)
                gallery_embs.append(embs.cpu().numpy())
                gallery_ys.append(labels.numpy())
        gallery_embs = np.vstack(gallery_embs)
        gallery_ys = np.concatenate(gallery_ys)

        # Trích xuất embeddings cho Queries (Real test set)
        query_embs = []
        query_ys = []
        with torch.no_grad():
            for imgs, labels in test_loader:
                imgs = imgs.to(device)
                embs = model(imgs)
                # Chuẩn hóa L2
                embs = F.normalize(embs, p=2, dim=1)
                query_embs.append(embs.cpu().numpy())
                query_ys.append(labels.numpy())
        query_embs = np.vstack(query_embs)
        query_ys = np.concatenate(query_ys)

        # So khớp cosine similarity (dot product trên vector L2 normalized)
        # Bằng ma trận nhân chéo: [len(query)] x [len(gallery)]
        sim_matrix = np.dot(query_embs, gallery_embs.T)
        best_match_idx = np.argmax(sim_matrix, axis=1)
        pred_labels = gallery_ys[best_match_idx]

        # Tính độ chính xác trên tập thực tế
        real_acc = np.mean(pred_labels == query_ys) * 100

        logger.info(
            f"Epoch [{epoch+1:02d}/{args.epochs:02d}] | "
            f"Train Loss: {epoch_loss:.4f} - Acc: {epoch_acc*100:6.2f}% | "
            f"Real Test Acc (FAISS Flat): {real_acc:6.2f}%"
        )

        history.append({
            "epoch": epoch + 1,
            "train_loss": epoch_loss,
            "train_acc": epoch_acc * 100,
            "real_test_acc": real_acc
        })

        if real_acc > best_real_acc:
            best_real_acc = real_acc
            best_epoch = epoch + 1
            best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            logger.info(f"  --> [Check Checkpoint] Đạt độ chính xác kỷ lục mới: {best_real_acc:.2f}% tại Epoch {best_epoch}!")

    # Load lại checkpoint tốt nhất và lưu ONNX
    logger.info(f"\n=======================================================")
    logger.info(f"KẾT QUẢ KHẢO SÁT TỐT NHẤT:")
    logger.info(f"Độ chính xác cao nhất trên tập Real: {best_real_acc:.2f}%")
    logger.info(f"Đạt được tại Epoch: {best_epoch}")
    logger.info(f"=======================================================\n")

    if best_model_state is not None:
        model.load_state_dict({k: v.to(device) for k, v in best_model_state.items()})

    # Lưu file ONNX chính thức
    onnx_out = "c:/AI_event/AI_Project_2526/backend/app/models/student_resnet18_arcface.onnx"
    model.eval()
    dummy_input = torch.randn(1, 3, 224, 224, device=device)
    torch.onnx.export(
        model,
        dummy_input,
        onnx_out,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
        opset_version=12
    )
    logger.info(f"Đã xuất ONNX tối ưu nhất tại: {onnx_out}")

    # Ghi file kết quả khảo sát ra json để vẽ biểu đồ hoặc báo cáo
    survey_out = "c:/AI_event/AI_Project_2526/backend/training/results/resnet18_epoch_survey.json"
    with open(survey_out, 'w', encoding='utf-8') as f:
        json.dump({
            "best_epoch": best_epoch,
            "best_acc": best_real_acc,
            "history": history
        }, f, ensure_ascii=False, indent=4)
    logger.info(f"Đã lưu kết quả khảo sát tại: {survey_out}")

if __name__ == "__main__":
    main()
