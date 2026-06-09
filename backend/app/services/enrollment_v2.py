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
    quality = assess_image_quality(bgr)
    reasons = []

    # Image quality checks
    if quality["blur_score"] <= 50:
        reasons.append("Image is blurry (Laplacian variance too low)")
    if quality["contrast"] <= 20:
        reasons.append("Low image contrast")
    if quality["brightness"] < 40 or quality["brightness"] > 220:
        reasons.append("Image brightness out of acceptable range")

    # Face size check
    if faces:
        face = faces[0]
        if not validate_face_size(face["bbox"], face["frame_shape"], min_px=80):
            reasons.append("Face region too small (< 80px)")

    return {
        "ok": len(reasons) == 0,
        "reasons": reasons,
        "blur_score": quality["blur_score"],
        "contrast": quality["contrast"],
        "brightness": quality["brightness"],
    }
