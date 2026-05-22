import asyncio
import uuid
from functools import partial

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import FaceEmbedding, User
from app.db.session import get_db
from app.schemas.api import FaceRegisterResponse
from app.services.attendance_logic import match_identity, next_faiss_id
from app.services.face_pipeline import FacePipeline
from app.services.faiss_indexer import FaissFaceIndex
from app.services.enrollment_v2 import generate_augmented_embeddings, assess_enrollment_quality

router = APIRouter(prefix="/faces", tags=["faces"])


def get_pipeline(request: Request) -> FacePipeline:
    return request.app.state.face_pipeline


def get_faiss(request: Request) -> FaissFaceIndex:
    return request.app.state.faiss_index


def _run_face_processing(pipeline: FacePipeline, img: np.ndarray):
    """
    Blocking CPU-heavy work — runs in a thread pool via run_in_executor
    so it never blocks the uvicorn event loop.
    Returns (faces, quality, embeddings) or raises.
    """
    # Step 1: face detection + quality gate
    faces = pipeline.process_frame_sync(img, use_adaptive_clahe=True)
    v = pipeline.validate_single_face(faces, min_det=0.65, min_face_size=80)

    if not v["ok"]:
        return {"error": v["reason"]}

    face = v["face"]

    # Step 2: enrollment quality assessment
    quality = assess_enrollment_quality(img, faces, None)
    if not quality["ok"]:
        return {"error": "quality", "reasons": quality["reasons"]}

    # Step 3: augmented embeddings (the slow part)
    def process_for_augment(frame):
        results = pipeline.process_frame_sync(frame, use_adaptive_clahe=True)
        return results if results else []

    embeddings = generate_augmented_embeddings(
        img,
        process_for_augment,
        n_geometric=7,
        n_photo=5,
        n_combined=2,
        n_occlusion=2,
    )

    return {
        "face": face,
        "embeddings": embeddings,
    }


@router.post("/register", response_model=FaceRegisterResponse)
async def register_face(
    request: Request,
    user_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> FaceRegisterResponse:
    """Register face with multi-embedding augmentation."""
    pipeline: FacePipeline = get_pipeline(request)
    faiss_index: FaissFaceIndex = get_faiss(request)
    u = await session.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")

    data = await file.read()
    img = pipeline.decode_image_bytes(data)

    # Run all blocking CPU work in a thread — keeps the event loop free
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,  # uses the default ThreadPoolExecutor
        partial(_run_face_processing, pipeline, img),
    )

    # Handle errors returned from the thread
    if "error" in result:
        err = result["error"]
        if err == "no_face":
            raise HTTPException(400, "Không phát hiện khuôn mặt đủ chất lượng")
        if err == "multiple_faces":
            raise HTTPException(400, "Nhiều khuôn mặt trong ảnh — hãy chụp một người")
        if err == "quality":
            reasons = result.get("reasons", [])
            raise HTTPException(400, f"Chất lượng ảnh không đạt: {', '.join(reasons)}")
        raise HTTPException(500, "Lỗi xử lý khuôn mặt")

    face = result["face"]
    embeddings = result["embeddings"]

    if not embeddings:
        raise HTTPException(500, "Không thể trích xuất embedding từ ảnh")

    # Store all embeddings in FAISS (async DB calls are fine here)
    first_det_score = float(face["det_score"])
    stored_ids = []
    fe = None

    for i, emb in enumerate(embeddings):
        fid = await next_faiss_id(session)
        emb_bytes = np.asarray(emb, dtype=np.float32).tobytes()
        fe = FaceEmbedding(
            user_id=user_id,
            faiss_id=fid,
            embedding_dim=len(emb),
            embedding_vector=emb_bytes,
            image_path=f"{file.filename}_aug{i:02d}" if i > 0 else file.filename,
        )
        session.add(fe)
        await session.flush()
        faiss_index.add_with_id(emb, fid, fe.id, user_id)
        stored_ids.append(fid)

    # FAISS persist is also blocking I/O — run in executor
    await loop.run_in_executor(None, faiss_index.persist)
    await session.commit()
    await session.refresh(fe)

    return FaceRegisterResponse(
        user_id=user_id,
        embedding_id=fe.id,
        faiss_id=stored_ids[0],
        det_score=first_det_score,
    )


@router.post("/match-debug")
async def match_debug(
    request: Request,
    file: UploadFile = File(...),
) -> dict:
    pipeline = get_pipeline(request)
    faiss_index = get_faiss(request)
    data = await file.read()
    img = pipeline.decode_image_bytes(data)

    loop = asyncio.get_event_loop()
    faces = await loop.run_in_executor(
        None,
        partial(pipeline.process_frame_sync, img, True),
    )

    if not faces:
        return {"hits": [], "message": "no_face"}
    faces.sort(key=lambda x: x["det_score"], reverse=True)
    emb = faces[0]["embedding"]
    m = match_identity(faiss_index, emb)
    return {
        "match": m,
        "bbox": faces[0]["bbox"],
        "settings": {"threshold": get_settings().recognition_threshold},
    }
