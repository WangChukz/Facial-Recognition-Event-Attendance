"""
enrollment_v2.py — Enhanced enrollment with data augmentation.
Generates multiple embeddings from single enrollment image to improve recognition accuracy.
"""
from typing import List
import cv2
import numpy as np

from app.services.augmentation import (
    assess_image_quality,
    crop_face_with_margin,
    validate_face_size,
    filter_embeddings,
    GEO_AUG,
    PHOTO_AUG,
    OCC_AUG,
    COMBINED_AUG,
)


def generate_augmented_embeddings(
    image: np.ndarray,
    process_face_fn,
    n_geometric: int = 7,
    n_photo: int = 5,
    n_combined: int = 2,
    n_occlusion: int = 2,
) -> List[np.ndarray]:
    """Generate multiple embeddings via augmentation on full image.

    Args:
        image: Full image (not cropped face)
        process_face_fn: Function to extract embedding (process_frame_sync)
        n_geometric: Number of geometric variants
        n_photo: Number of photometric variants
        n_combined: Number of combined augmentations
        n_occlusion: Number of occlusion variants

    Returns:
        List of valid embeddings (1 + augmented variants)
    """
    embeddings = []
    det_score_threshold = 0.50  # Threshold for extracted embeddings

    # Original embedding from full image
    try:
        faces = process_face_fn(image)
        if faces and len(faces) > 0:
            embedding = faces[0].get("embedding")
            det_score = faces[0].get("det_score", 0)
            if embedding is not None and det_score >= det_score_threshold:
                embeddings.append(embedding)
    except Exception as e:
        pass

    if not embeddings:
        return []

    configs = [
        (GEO_AUG, n_geometric),
        (PHOTO_AUG, n_photo),
        (COMBINED_AUG, n_combined),
        (OCC_AUG, n_occlusion),
    ]

    for aug_pipeline, target_count in configs:
        attempts = 0
        max_attempts = target_count * 3
        added = 0

        while added < target_count and attempts < max_attempts:
            attempts += 1
            try:
                aug_result = aug_pipeline(image=image)
                aug_img = aug_result["image"]

                faces = process_face_fn(aug_img)
                if faces and len(faces) > 0:
                    embedding = faces[0].get("embedding")
                    det_score = faces[0].get("det_score", 0)
                    if embedding is not None and det_score >= det_score_threshold:
                        embeddings.append(embedding)
                        added += 1
            except Exception:
                continue

    # Filter out noisy embeddings
    if embeddings:
        filtered = filter_embeddings(embeddings, min_similarity=0.35, max_similarity=0.99)
        return filtered if filtered else [embeddings[0]]  # Keep at least original
    return embeddings


def assess_enrollment_quality(
    bgr: np.ndarray,
    faces: list,
    face_crop: np.ndarray,
) -> dict:
    """Comprehensive quality assessment for enrollment image.

    Returns dict with 'ok' bool and 'reasons' list.
    """
    target_img = bgr
    if faces:
        h, w = bgr.shape[:2]
        bbox = faces[0]["bbox"]
        x1 = max(0, int(bbox[0]))
        y1 = max(0, int(bbox[1]))
        x2 = min(w, int(bbox[2]))
        y2 = min(h, int(bbox[3]))
        if (x2 - x1) > 10 and (y2 - y1) > 10:
            target_img = bgr[y1:y2, x1:x2]

    quality = assess_image_quality(target_img)
    reasons = []

    # Image quality checks (relaxed thresholds for portrait/card photos)
    if quality["blur_score"] <= 8:
        reasons.append("Ảnh bị mờ (Độ sắc nét quá thấp)")
    if quality["contrast"] <= 5:
        reasons.append("Độ tương phản của ảnh quá thấp")
    if quality["brightness"] < 25 or quality["brightness"] > 235:
        reasons.append("Độ sáng của ảnh nằm ngoài phạm vi cho phép")

    # Face size check
    if faces:
        face = faces[0]
        if not validate_face_size(face["bbox"], face["frame_shape"], min_px=60):
            reasons.append("Khuôn mặt quá nhỏ (phải lớn hơn 60px)")

    return {
        "ok": len(reasons) == 0,
        "reasons": reasons,
        "blur_score": quality["blur_score"],
        "contrast": quality["contrast"],
        "brightness": quality["brightness"],
    }
