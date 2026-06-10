"""
Trích xuất embeddings từ dữ liệu ảnh người lạ mạng (data_mạng)
để dùng trong Case 4 - Unknown Rejection testing
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from insightface.app import FaceAnalysis


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
TRAINING = BACKEND / "training"
MODELS_DIR = ROOT / "ai_models"
DATASET = Path(r"C:\AI_event\dataset\dataset")
NETWORK_DATA = DATASET / "data_mạng" / "data_mạng"

OUTPUT_EMBEDDINGS = TRAINING / "network_embeddings.npy"
OUTPUT_METADATA = TRAINING / "network_embeddings_metadata.json"


def setup_face_model() -> FaceAnalysis:
    """Khởi tạo mô hình InsightFace buffalo_l"""
    model_path = MODELS_DIR / "models" / "buffalo_l"
    if not model_path.exists():
        print(f"⚠️  Model path not found: {model_path}")
        print("Falling back to default model download...")
        app = FaceAnalysis(name="buffalo_l", root=str(MODELS_DIR / "models"), allowed_modules=["detection", "recognition"])
    else:
        app = FaceAnalysis(name="buffalo_l", root=str(MODELS_DIR / "models"), allowed_modules=["detection", "recognition"])

    # Lower detection threshold for better sensitivity with small images
    app.prepare(ctx_id=0, det_thresh=0.1, det_size=(640, 480))
    print(f"[OK] Model loaded: buffalo_l (det_thresh=0.1, optimized for small images)")
    return app


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """Chuẩn hóa embedding thành L2"""
    norm = np.linalg.norm(embedding)
    if norm > 0:
        return embedding / norm
    return embedding


def extract_face_embedding(image_path: Path, app: FaceAnalysis) -> np.ndarray | None:
    """Trích xuất embedding từ một ảnh (hỗ trợ Vietnamese file names & small images)"""
    try:
        # Use cv2.imdecode for proper Unicode path handling on Windows
        img_array = np.fromfile(str(image_path), np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img is None or img.size == 0:
            return None

        # If image is very small, upscale it for better face detection
        h, w = img.shape[:2]
        if h < 200 or w < 200:
            scale = max(1, int(np.ceil(240 / max(h, w))))
            img = cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

        faces = app.get(img)
        if len(faces) == 0:
            return None

        # Lấy khuôn mặt lớn nhất (có confidence cao nhất)
        best_face = max(faces, key=lambda x: x.bbox[2] * x.bbox[3] if hasattr(x, 'bbox') else 0)
        embedding = best_face.embedding.astype(np.float32)
        return normalize_embedding(embedding)
    except Exception as e:
        print(f"  [-] Error in {image_path.name}: {str(e)[:50]}")
        return None


def process_network_images() -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Quét toàn bộ thư mục data_mạng và trích embeddings"""
    if not NETWORK_DATA.exists():
        raise FileNotFoundError(f"Network data folder not found: {NETWORK_DATA}")

    app = setup_face_model()
    embeddings: list[np.ndarray] = []
    metadata: list[dict[str, Any]] = []

    # Lấy danh sách tất cả ảnh
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
    image_files = [f for f in NETWORK_DATA.rglob('*') if f.suffix.lower() in image_extensions]

    print(f"[*] Found {len(image_files)} image files in network data folder")

    if len(image_files) == 0:
        raise ValueError(f"No image files found in {NETWORK_DATA}")

    t0 = time.time()
    processed = 0

    for idx, image_path in enumerate(image_files, 1):
        if idx % 10 == 0:
            print(f"    Processing {idx}/{len(image_files)}...", end='\r')

        embedding = extract_face_embedding(image_path, app)
        if embedding is not None:
            embeddings.append(embedding)
            person_name = image_path.parent.name
            metadata.append({
                "id": len(embeddings) - 1,
                "image_path": str(image_path.relative_to(DATASET)),
                "person": person_name,
            })
            processed += 1

    elapsed = time.time() - t0
    print(f"\n[OK] Processed {processed}/{len(image_files)} images in {elapsed:.1f}s")

    if len(embeddings) == 0:
        raise ValueError("No valid face embeddings extracted")

    result = np.array(embeddings, dtype=np.float32)
    print(f"[*] Embeddings shape: {result.shape}")

    return result, metadata


def save_results(embeddings: np.ndarray, metadata: list[dict[str, Any]]) -> None:
    """Lưu embeddings và metadata"""
    np.save(OUTPUT_EMBEDDINGS, embeddings)
    print(f"[OK] Saved embeddings to {OUTPUT_EMBEDDINGS}")

    with OUTPUT_METADATA.open("w", encoding="utf-8") as f:
        json.dump({
            "total": len(embeddings),
            "embedding_dim": embeddings.shape[1],
            "samples": metadata,
        }, f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved metadata to {OUTPUT_METADATA}")


def main() -> None:
    print("=" * 60)
    print("[*] Extract Network Image Embeddings for Unknown Rejection Testing")
    print("=" * 60)

    try:
        embeddings, metadata = process_network_images()
        save_results(embeddings, metadata)

        print("\n" + "=" * 60)
        print("[OK] Successfully extracted network embeddings!")
        print(f"     Total embeddings: {len(metadata)}")
        print(f"     Output files:")
        print(f"     - {OUTPUT_EMBEDDINGS}")
        print(f"     - {OUTPUT_METADATA}")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
