from __future__ import annotations

import base64
import concurrent.futures
import threading
from typing import Any

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from app.config import get_settings


class FacePipeline:
    """Face detection + alignment + embedding (InsightFace ArcFace)."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, self._settings.frame_process_workers)
        )
        self._model: FaceAnalysis | None = None
        self._model_lock = threading.Lock()

    def _ensure_model(self) -> FaceAnalysis:
        with self._model_lock:
            if self._model is None:
                providers = [p.strip() for p in self._settings.onnx_providers.split(",") if p.strip()]
                self._model = FaceAnalysis(
                    name=self._settings.insightface_model,
                    providers=providers,
                )
                self._model.prepare(
                    ctx_id=self._settings.insightface_ctx_id,
                    det_size=(self._settings.det_size_width, self._settings.det_size_height),
                )
            return self._model

    def decode_image_b64(self, b64: str) -> np.ndarray:
        raw = base64.b64decode(b64)
        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Invalid image data")
        return img

    def decode_image_bytes(self, data: bytes) -> np.ndarray:
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Invalid image data")
        return img

    def preprocess_image(self, bgr: np.ndarray) -> np.ndarray:
        """CLAHE with fixed clipLimit=2.5 (legacy). Use preprocess_image_v2() for adaptive."""
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    def preprocess_image_v2(self, bgr: np.ndarray) -> np.ndarray:
        """Adaptive CLAHE: clipLimit adjusted based on image brightness.
        Addresses backlight, spotlight, and uneven lighting in event venues."""
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        l, a, b_ch = cv2.split(lab)

        mean_l = l.mean()
        if mean_l < 80:      # dark image
            clip = 3.5
        elif mean_l > 180:   # overexposed
            clip = 1.5
        else:                # normal lighting
            clip = 2.0

        clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
        cl = clahe.apply(l)

        gaussian = cv2.GaussianBlur(cl, (5, 5), 1.0)
        cl = np.clip(cv2.addWeighted(cl, 1.3, gaussian, -0.3, 0), 0, 255).astype(np.uint8)

        limg = cv2.merge((cl, a, b_ch))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    def process_frame_sync(self, bgr: np.ndarray, use_adaptive_clahe: bool = True) -> list[dict[str, Any]]:
        """Process image: detect faces, align, extract embeddings.

        Args:
            bgr: Input image in BGR format
            use_adaptive_clahe: Use adaptive v2 preprocessing (recommended for enrollment)
        """
        processed_bgr = self.preprocess_image_v2(bgr) if use_adaptive_clahe else self.preprocess_image(bgr)

        model = self._ensure_model()
        faces = model.get(processed_bgr)
        h, w = bgr.shape[:2]
        results: list[dict[str, Any]] = []
        for f in faces:
            box = f.bbox.astype(int).tolist()
            emb = np.asarray(f.embedding, dtype=np.float32)
            results.append(
                {
                    "bbox": box,
                    "det_score": float(f.det_score),
                    "embedding": emb,
                    "kps": f.kps.tolist() if f.kps is not None else None,
                    "frame_shape": [h, w],
                }
            )
        return results

    async def process_frame(self, bgr: np.ndarray) -> list[dict[str, Any]]:
        loop = __import__("asyncio").get_event_loop()
        return await loop.run_in_executor(self._executor, self.process_frame_sync, bgr)

    def process_b64_sync(self, b64: str) -> tuple[np.ndarray, list[dict[str, Any]]]:
        img = self.decode_image_b64(b64)
        return img, self.process_frame_sync(img)

    def validate_single_face(
        self,
        faces: list[dict[str, Any]],
        min_det: float = 0.65,
        min_face_size: int = 80,
    ) -> dict[str, Any]:
        """Validate single face with strict quality gates.

        Args:
            faces: Detection results from process_frame_sync
            min_det: Minimum detection score (increased from 0.5 to 0.65)
            min_face_size: Minimum face width/height in pixels
        """
        from app.services.augmentation import validate_face_size

        good = [f for f in faces if f["det_score"] >= min_det and validate_face_size(f["bbox"], f["frame_shape"], min_face_size)]
        if len(good) == 0:
            return {"ok": False, "reason": "no_face", "face": None}
        if len(good) > 1:
            good.sort(key=lambda x: x["det_score"], reverse=True)
            return {"ok": False, "reason": "multiple_faces", "face": good[0]}
        return {"ok": True, "reason": None, "face": good[0]}
