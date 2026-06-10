import cv2
import numpy as np
import albumentations as A
from typing import List

def build_geometric_aug() -> A.Compose:
    """Geometric transforms to simulate different pose angles and distances."""
    return A.Compose([
        A.Rotate(limit=(-20, 20), border_mode=cv2.BORDER_REPLICATE, p=1.0),
        A.HorizontalFlip(p=0.5),
        A.Perspective(scale=(0.02, 0.06), p=0.7),
        A.ShiftScaleRotate(
            shift_limit=0.08, scale_limit=(-0.1, 0.2),
            rotate_limit=0, border_mode=cv2.BORDER_REPLICATE, p=0.8
        ),
    ])

def build_photometric_aug() -> A.Compose:
    """Photometric transforms to simulate different lighting conditions."""
    return A.Compose([
        A.OneOf([
            A.RandomBrightnessContrast(brightness_limit=0.35, contrast_limit=0.35, p=1.0),
            A.RandomGamma(gamma_limit=(60, 140), p=1.0),
            A.CLAHE(clip_limit=(1.0, 4.0), tile_grid_size=(4, 4), p=1.0),
        ], p=0.9),
        A.OneOf([
            A.GaussNoise(var_limit=(5.0, 30.0), p=1.0),
            A.ISONoise(color_shift=(0.01, 0.05), p=1.0),
        ], p=0.6),
        A.OneOf([
            A.MotionBlur(blur_limit=5, p=1.0),
            A.GaussianBlur(blur_limit=(3, 5), p=1.0),
        ], p=0.4),
        A.HueSaturationValue(
            hue_shift_limit=8, sat_shift_limit=20, val_shift_limit=20, p=0.5
        ),
    ])

def build_occlusion_aug() -> A.Compose:
    """Occlusion transforms to simulate glasses, masks, etc."""
    return A.Compose([
        A.CoarseDropout(
            max_holes=3, max_height=30, max_width=30,
            min_holes=1, min_height=10, min_width=10,
            fill_value=0, p=0.4
        ),
    ])

def build_combined_aug() -> A.Compose:
    """Combined geometric + photometric augmentation."""
    return A.Compose([
        build_photometric_aug(),
        build_geometric_aug(),
    ])

GEO_AUG = build_geometric_aug()
PHOTO_AUG = build_photometric_aug()
OCC_AUG = build_occlusion_aug()
COMBINED_AUG = build_combined_aug()

def assess_image_quality(bgr: np.ndarray) -> dict:
    """Quality assessment gate to reject poor enrollment images."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = bgr.shape[:2]

    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    mean_brightness = gray.mean()
    contrast = gray.std()

    return {
        'blur_score': blur_score,
        'brightness': mean_brightness,
        'contrast': contrast,
        'ok': blur_score > 50 and contrast > 20 and mean_brightness > 40 and mean_brightness < 220,
    }

def crop_face_with_margin(bgr: np.ndarray, bbox: list, margin: float = 0.25) -> np.ndarray:
    """Crop face region with margin for augmentation flexibility."""
    x1, y1, x2, y2 = [int(v) for v in bbox]
    face_w, face_h = x2 - x1, y2 - y1

    mx = int(face_w * margin)
    my = int(face_h * margin)

    h, w = bgr.shape[:2]
    x1c = max(0, x1 - mx)
    y1c = max(0, y1 - my)
    x2c = min(w, x2 + mx)
    y2c = min(h, y2 + my)

    face_crop = bgr[y1c:y2c, x1c:x2c]
    return cv2.resize(face_crop, (256, 256), interpolation=cv2.INTER_LANCZOS4)

def validate_face_size(bbox: list, img_shape: tuple, min_px: int = 80) -> bool:
    """Reject faces smaller than minimum pixel threshold."""
    x1, y1, x2, y2 = bbox
    face_w, face_h = x2 - x1, y2 - y1
    return face_w >= min_px and face_h >= min_px

def filter_embeddings(
    embeddings: List[np.ndarray],
    min_similarity: float = 0.35,
    max_similarity: float = 0.99,
) -> List[np.ndarray]:
    """Remove embeddings too different or too similar to original."""
    if not embeddings:
        return []

    orig = np.asarray(embeddings[0], dtype=np.float32).reshape(-1)
    orig_norm = np.linalg.norm(orig)
    if orig_norm > 0:
        orig = orig / orig_norm
    filtered = [embeddings[0]]

    for emb in embeddings[1:]:
        candidate = np.asarray(emb, dtype=np.float32).reshape(-1)
        candidate_norm = np.linalg.norm(candidate)
        if candidate_norm > 0:
            candidate = candidate / candidate_norm
        sim = float(np.dot(orig, candidate))
        if min_similarity <= sim <= max_similarity:
            filtered.append(emb)

    return filtered

def calibrate_threshold(
    same_user_scores: List[float],
    diff_user_scores: List[float],
) -> tuple[float, float]:
    """Find optimal similarity threshold for recognition."""
    thresholds = np.arange(0.3, 0.8, 0.01)
    best_threshold, best_accuracy = 0, 0

    for threshold in thresholds:
        tp = sum(1 for s in same_user_scores if s >= threshold)
        fn = sum(1 for s in same_user_scores if s < threshold)
        tn = sum(1 for s in diff_user_scores if s < threshold)
        fp = sum(1 for s in diff_user_scores if s >= threshold)

        total = tp + tn + fp + fn
        accuracy = (tp + tn) / total if total > 0 else 0

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = threshold

    return best_threshold, best_accuracy
