# app/services/augmentation.py
# Chuyển tiếp (proxy) các hàm augmentation sang cấu trúc AI Core mới để giữ tương thích

from app.ai_core.utils.augmentation import (
    build_geometric_aug,
    build_photometric_aug,
    build_occlusion_aug,
    build_combined_aug,
    GEO_AUG,
    PHOTO_AUG,
    OCC_AUG,
    COMBINED_AUG,
    assess_image_quality,
    crop_face_with_margin,
    validate_face_size,
    filter_embeddings,
    calibrate_threshold
)
