import os
import sys
import time
import json
import logging
import argparse
from typing import Tuple

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, random_split
import torchvision.models as models
import torchvision.transforms as transforms

# Cấu hình UTF-8 để hiển thị tiếng Việt mượt mà trên Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Thiết lập Logger chuyên nghiệp
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ArcFace_Trainer")

# Định nghĩa toán tử tổn thất ArcFace (Additive Angular Margin Loss)
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
        # Chuẩn hóa L2 cho đặc trưng đầu vào và ma trận trọng số
        cos_theta = F.linear(F.normalize(input), F.normalize(self.weight))
        
        # Tính sin(theta) = sqrt(1 - cos^2(theta))
        sine = torch.sqrt((1.0 - torch.pow(cos_theta, 2)).clamp(0, 1))
        
        # Tính cos(theta + m) = cos(theta)*cos(m) - sin(theta)*sin(m)
        phi = cos_theta * np.cos(self.m) - sine * np.sin(self.m)
        
        # Ngăn chặn cos(theta + m) vượt quá giới hạn bằng cách nới lỏng khi cos(theta) < 0
        phi = torch.where(cos_theta > 0, phi, cos_theta)
        
        # Chuyển nhãn lớp sang dạng One-hot vector
        one_hot = torch.zeros(cos_theta.size(), device=input.device)
        one_hot.scatter_(1, label.view(-1, 1).long(), 1)
        
        # Kết hợp: đúng lớp dùng phi = cos(theta + m), sai lớp giữ nguyên cos(theta).
        output = (one_hot * phi) + ((1.0 - one_hot) * cos_theta)
        
        # Nhân tỷ lệ phóng đại s
        output *= self.s
        return output


# Bộ đọc dữ liệu PyTorch Dataset đọc ảnh từ cấu trúc thư mục sinh viên và ánh xạ metadata
class StudentDataset(Dataset):
    def __init__(self, data_dir: str, transform=None, meta_path: str = None, enroll_dir: str = None):
        self.data_dir = data_dir
        self.transform = transform
        self.image_paths = []
        self.labels = []
        self.label_map = {}

        if not os.path.exists(data_dir):
            raise FileNotFoundError(f"Thư mục dataset '{data_dir}' không tồn tại.")

        # Tìm kiếm và tải file metadata.xlsx
        if not meta_path:
            meta_path = "c:/AI_event/dataset/dataset/metadata.xlsx"
            if not os.path.exists(meta_path):
                meta_path = os.path.join(os.path.dirname(data_dir), "metadata.xlsx")
                
        meta_map = {}
        if os.path.exists(meta_path):
            try:
                import pandas as pd
                import unicodedata
                import re
                df_meta = pd.read_excel(meta_path)
                logger.info(f"Đã nạp file metadata thành công: {meta_path} (Tìm thấy {len(df_meta)} sinh viên)")
                
                def remove_vietnamese_diacritics(text):
                    if not isinstance(text, str):
                        return ""
                    text = unicodedata.normalize('NFD', text)
                    text = re.sub(r'[\u0300-\u036f]', '', text)
                    text = text.replace('đ', 'd').replace('Đ', 'D')
                    text = unicodedata.normalize('NFC', text)
                    text = text.replace(' ', '')
                    return text

                for _, row in df_meta.iterrows():
                    name = str(row.get('Họ và tên', '')).strip()
                    student_id = str(row.get('Mã sinh viên', '')).strip()
                    sclass = str(row.get('Lớp', '')).strip()
                    dob = str(row.get('Ngày sinh', '')).strip().split()[0] if row.get('Ngày sinh') else ""
                    
                    clean_name = remove_vietnamese_diacritics(name).lower()
                    meta_map[clean_name] = {
                        "student_id": student_id,
                        "name": name,
                        "class": sclass,
                        "dob": dob
                    }
            except Exception as e:
                logger.error(f"Lỗi khi đọc file metadata trong Dataset: {str(e)}")
        else:
            logger.warning(f"Không tìm thấy file metadata.xlsx tại: {meta_path}.")

        student_folders = sorted([
            f for f in os.listdir(data_dir) 
            if os.path.isdir(os.path.join(data_dir, f)) and not f.startswith(".")
        ])

        valid_extensions = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

        for idx, folder in enumerate(student_folders):
            # So khớp không dấu và biệt lệ PhamTrungKien -> Nguyễn Trung Kiên
            clean_folder = folder.replace("_real", "").lower()
            if clean_folder == "phamtrungkien":
                clean_folder = "nguyentrungkien"
                
            student_info = meta_map.get(clean_folder)
            if student_info:
                self.label_map[idx] = {
                    "student_id": student_info["student_id"],
                    "name": student_info["name"],
                    "class": student_info["class"],
                    "dob": student_info["dob"],
                    "folder_name": folder,
                    "clean_name": folder.replace("_real", "")
                }
            else:
                self.label_map[idx] = {
                    "student_id": folder.replace("_real", ""),
                    "name": folder.replace("_real", ""),
                    "class": "Unknown",
                    "dob": "",
                    "folder_name": folder,
                    "clean_name": folder.replace("_real", "")
                }
                
            # 1. Đọc tất cả ảnh thực tế hiện trường lớp học
            folder_path = os.path.join(data_dir, folder)
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(valid_extensions):
                        self.image_paths.append(os.path.join(root, file))
                        self.labels.append(idx)
            
            # 2. Gộp ảnh thẻ đăng ký tương ứng từ enroll_dir (giải quyết Domain Gap)
            if enroll_dir and os.path.exists(enroll_dir):
                import re
                enroll_files = [f for f in os.listdir(enroll_dir) if f.lower().endswith(valid_extensions)]
                for ef in enroll_files:
                    ef_clean = re.sub(r'_enroll\.(jpg|png|jpeg|webp|bmp)', '', ef, flags=re.IGNORECASE).lower()
                    if ef_clean == clean_folder:
                        self.image_paths.append(os.path.join(enroll_dir, ef))
                        self.labels.append(idx)
                        logger.info(f"  -> Đã gộp thành công ảnh thẻ enroll cho SV '{self.label_map[idx]['name']}': {ef}")

        logger.info(f"Dataset Loaded: {len(self.image_paths)} images across {len(student_folders)} classes.")

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        label = self.labels[idx]
        
        try:
            # Đọc ảnh OpenCV (BGR -> RGB) hỗ trợ Unicode trên Windows
            img_array = np.fromfile(img_path, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Không thể giải mã ảnh (img là None)")
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            if self.transform:
                from PIL import Image
                img_pil = Image.fromarray(img)
                img = self.transform(img_pil)
                
            return img, torch.tensor(label, dtype=torch.long)
        except Exception as e:
            logger.warning(f"Lỗi đọc ảnh {img_path} tại index {idx}: {str(e)}. Đang thử chọn một ảnh ngẫu nhiên khác...")
            import random
            rand_idx = random.randint(0, len(self.image_paths) - 1)
            return self.__getitem__(rand_idx)



# Kiến trúc mạng Backbone ResNet18 tối ưu hóa cho nhận diện khuôn mặt
class FaceNetResNet18(nn.Module):
    def __init__(self, embedding_dim: int = 512):
        super(FaceNetResNet18, self).__init__()
        # Sử dụng ResNet-18 pre-trained ImageNet làm nền tảng
        self.backbone = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        
        # Thay thế tầng Fully Connected cuối để xuất ra vector embedding 512-D
        in_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Sequential(
            nn.Linear(in_features, embedding_dim),
            nn.BatchNorm1d(embedding_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)


def parse_args():
    parser = argparse.ArgumentParser(description="Huấn luyện tinh chỉnh PyTorch ArcFace cho Sinh viên Học viện Ngân hàng.")
    parser.add_argument("--data_dir", type=str, default="c:/AI_event/dataset/dataset/real", help="Thư mục chứa ảnh thực tế (real)")
    parser.add_argument("--enroll_dir", type=str, default="c:/AI_event/dataset/dataset/enroll", help="Thư mục chứa ảnh thẻ đăng ký (enroll)")
    parser.add_argument("--epochs", type=int, default=20, help="Số lượng Epochs huấn luyện.")
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--onnx_out", type=str, default="c:/AI_event/AI_Project_2526/backend/app/models/student_resnet18_arcface.onnx")
    parser.add_argument("--label_out", type=str, default="c:/AI_event/AI_Project_2526/backend/app/models/label_encoder_pytorch.json")
    return parser.parse_args()


def export_model_to_onnx(model: nn.Module, save_path: str):
    """Xuất mô hình PyTorch đã tinh chỉnh sang định dạng ONNX."""
    logger.info(f"Đang tiến hành xuất mô hình sang ONNX tại: {save_path}")
    model.eval()
    dummy_input = torch.randn(1, 3, 224, 224, device=next(model.parameters()).device)
    
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    
    torch.onnx.export(
        model,
        dummy_input,
        save_path,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
        opset_version=12
    )
    logger.info("Xuất ONNX thành công!")


def main():
    args = parse_args()
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Thiết bị huấn luyện: {device}")

    # Pipeline biến đổi ảnh cho Train (có Augmentation để học từ 1 ảnh gốc)
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=(-15, 15)),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # Pipeline biến đổi ảnh cho Validation (chỉ resize và chuẩn hóa)
    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    class SubsetWithTransform(Dataset):
        def __init__(self, subset, transform):
            self.subset = subset
            self.transform = transform
        def __getitem__(self, idx):
            original_idx = self.subset.indices[idx]
            img_path = self.subset.dataset.image_paths[original_idx]
            label = self.subset.dataset.labels[original_idx]
            try:
                # Đọc ảnh OpenCV (BGR -> RGB) hỗ trợ Unicode trên Windows
                img_array = np.fromfile(img_path, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if img is None:
                    raise ValueError("Không thể giải mã ảnh (img là None)")
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                if self.transform:
                    from PIL import Image
                    img_pil = Image.fromarray(img)
                    img = self.transform(img_pil)
                return img, torch.tensor(label, dtype=torch.long)
            except Exception as e:
                import random
                rand_idx = random.randint(0, len(self.subset) - 1)
                return self.__getitem__(rand_idx)
        def __len__(self):
            return len(self.subset)

    try:
        logger.info(f"Đang tải tập dữ liệu gốc từ {args.data_dir}...")
        full_dataset = StudentDataset(args.data_dir, enroll_dir=args.enroll_dir)
        num_classes = len(full_dataset.label_map)
        
        # Chia train/val 80% / 20%
        val_size = int(len(full_dataset) * 0.2)
        train_size = len(full_dataset) - val_size
        
        subset_train, subset_val = random_split(
            full_dataset, 
            [train_size, val_size],
            generator=torch.Generator().manual_seed(42)
        )
        
        train_dataset = SubsetWithTransform(subset_train, train_transform)
        val_dataset = SubsetWithTransform(subset_val, val_transform)
        
        logger.info(f"Đã phân chia tập dữ liệu: Train = {len(train_dataset)} ảnh, Val = {len(val_dataset)} ảnh.")
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo dataset: {str(e)}")
        sys.exit(1)

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)


    # Khởi tạo mô hình
    model = FaceNetResNet18(embedding_dim=512).to(device)
    
    # Khởi tạo lớp ArcFace Loss
    arcface_head = ArcMarginProduct(in_features=512, out_features=num_classes, s=30.0, m=0.50).to(device)

    # Bộ tối ưu và hàm mất mát phân loại
    optimizer = optim.AdamW(
        list(model.parameters()) + list(arcface_head.parameters()), 
        lr=args.lr, 
        weight_decay=1e-4
    )
    criterion = nn.CrossEntropyLoss()

    logger.info("Bắt đầu quy trình huấn luyện tinh chỉnh (Fine-tuning Epochs)...")
    
    best_val_acc = -1.0
    best_val_loss = float('inf')
    best_model_state = None
    best_head_state = None
    
    patience = 15
    patience_counter = 0
    
    for epoch in range(args.epochs):
        model.train()
        arcface_head.train()
        train_loss = 0.0
        train_correct = 0
        total_train = 0

        t0 = time.time()

        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)

            optimizer.zero_grad()
            
            # 1. Trích xuất vector 512-D
            embeddings = model(imgs)
            
            # 2. Đưa qua lớp ArcFace Loss
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

        # Validation phase
        model.eval()
        arcface_head.eval()
        val_loss = 0.0
        val_correct = 0
        total_val = 0

        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                embeddings = model(imgs)
                outputs = arcface_head(embeddings, labels)
                loss = criterion(outputs, labels)

                val_loss += loss.item() * imgs.size(0)
                _, preds = torch.max(outputs, 1)
                val_correct += torch.sum(preds == labels.data).item()
                total_val += imgs.size(0)

        val_epoch_loss = val_loss / total_val if total_val > 0 else 0
        val_epoch_acc = val_correct / total_val if total_val > 0 else 0

        logger.info(
            f"Epoch [{epoch+1}/{args.epochs}] ({time.time() - t0:.1f}s) | "
            f"Train Loss: {epoch_loss:.4f} - Acc: {epoch_acc*100:.2f}% | "
            f"Val Loss: {val_epoch_loss:.4f} - Acc: {val_epoch_acc*100:.2f}%"
        )

        # Kiểm tra và cập nhật mô hình tốt nhất
        is_best = False
        if val_epoch_acc > best_val_acc:
            best_val_acc = val_epoch_acc
            best_val_loss = val_epoch_loss
            is_best = True
        elif abs(val_epoch_acc - best_val_acc) < 1e-6:
            if val_epoch_loss < best_val_loss:
                best_val_loss = val_epoch_loss
                is_best = True

        if is_best:
            best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            best_head_state = {k: v.cpu().clone() for k, v in arcface_head.state_dict().items()}
            patience_counter = 0
            logger.info(f"  --> [MỚI] Tìm thấy checkpoint tốt nhất tại Epoch {epoch+1}! Val Acc: {best_val_acc*100:.2f}%, Val Loss: {best_val_loss:.4f}")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Early Stopping được kích hoạt sau {patience} epoch không cải thiện. Dừng huấn luyện sớm tại Epoch {epoch+1}.")
                break

    # Khôi phục trạng thái mô hình tốt nhất trước khi lưu và xuất ONNX
    if best_model_state is not None:
        logger.info(f"Đang tải lại checkpoint tốt nhất từ Epoch đạt Val Acc: {best_val_acc*100:.2f}%")
        model.load_state_dict({k: v.to(device) for k, v in best_model_state.items()})
    else:
        logger.warning("Không tìm thấy checkpoint tốt nhất, sử dụng mô hình của epoch cuối cùng.")

    # Lưu mã hóa nhãn sinh viên
    with open(args.label_out, 'w', encoding='utf-8') as f:
        json.dump(full_dataset.label_map, f, ensure_ascii=False, indent=4)
    logger.info(f"Đã lưu Label Encoder PyTorch tại: {args.label_out}")

    # Xuất file ONNX
    export_model_to_onnx(model, args.onnx_out)
    logger.info("=== QUÁ TRÌNH HUẤN LUYỆN TINH CHỈNH PYTORCH HOÀN TẤT ===")


if __name__ == "__main__":
    main()
