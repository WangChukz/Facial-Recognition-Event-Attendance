from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from app.api import routes_attendance, routes_events, routes_faces, routes_users
from app.config import get_settings
from app.db.models import AttendanceDirection, AttendanceLog, Base, FaceEmbedding, User
from app.db.session import async_session_maker, engine
from app.services.attendance_logic import match_identity, should_log_attendance
from app.services.face_pipeline import FacePipeline
from app.services.faiss_indexer import FaissFaceIndex


async def rebuild_faiss_from_db(faiss_index: FaissFaceIndex) -> None:
    async with async_session_maker() as session:
        r = await session.execute(select(FaceEmbedding).order_by(FaceEmbedding.faiss_id))
        rows = list(r.scalars().all())
    faiss_index.clear_memory()
    if rows:
        faiss_index.dim = rows[0].embedding_dim
    for fe in rows:
        vec = np.frombuffer(fe.embedding_vector, dtype=np.float32).copy()
        faiss_index.add_with_id(vec, fe.faiss_id, fe.id, fe.user_id)
    faiss_index.persist()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    faiss_index = FaissFaceIndex(settings.faiss_index_path, settings.faiss_meta_path)
    faiss_index.load()
    app.state.faiss_index = faiss_index
    app.state.face_pipeline = FacePipeline()
    async with async_session_maker() as session:
        cr = await session.execute(select(func.count()).select_from(FaceEmbedding))
        db_count = int(cr.scalar_one())
    if db_count > 0 and faiss_index.total != db_count:
        await rebuild_faiss_from_db(faiss_index)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AI Event Face Attendance", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(routes_users.router, prefix="/api")
    app.include_router(routes_events.router, prefix="/api")
    app.include_router(routes_faces.router, prefix="/api")
    app.include_router(routes_attendance.router, prefix="/api")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.websocket("/api/ws/live")
    async def ws_live(
        websocket: WebSocket,
        event_id: uuid.UUID | None = Query(None),
        session_id: uuid.UUID | None = Query(None),
        auto_attendance: bool = Query(True),
    ) -> None:
        await websocket.accept()
        try:
            while True:
                raw = await websocket.receive_text()
                data = json.loads(raw)
                if data.get("type") != "frame":
                    await websocket.send_json({"error": "expected type=frame", "faces": []})
                    continue
                import time
                t0 = time.perf_counter()
                b64 = data.get("image", "")
                pipeline: FacePipeline = websocket.app.state.face_pipeline
                faiss_index: FaissFaceIndex = websocket.app.state.faiss_index
                
                t_decode_start = time.perf_counter()
                img = pipeline.decode_image_b64(b64)
                t_decode_end = time.perf_counter()
                
                t_detect_start = time.perf_counter()
                faces = await pipeline.process_frame(img)
                t_detect_end = time.perf_counter()
                
                t_match_start = time.perf_counter()
                frame_shape = faces[0]["frame_shape"] if faces else list(img.shape[:2])
                out_faces: list[dict] = []
                async with async_session_maker() as db:
                    for face in faces:
                        m = match_identity(faiss_index, face["embedding"])
                        item: dict = {
                            "bbox": face["bbox"],
                            "det_score": face["det_score"],
                            "status": m["status"],
                            "similarity": m.get("similarity"),
                            "user_id": None,
                            "full_name": None,
                            "attendance_logged": False,
                        }
                        if m["status"] == "known" and m.get("user_id"):
                            uid = m["user_id"]
                            u = await db.get(User, uid)
                            item["user_id"] = str(uid)
                            item["full_name"] = u.full_name if u else None
                            if auto_attendance and event_id is not None:
                                ok, reason = await should_log_attendance(
                                    db,
                                    user_id=uid,
                                    event_id=event_id,
                                    direction=AttendanceDirection.check_in,
                                )
                                if ok:
                                    db.add(
                                        AttendanceLog(
                                            user_id=uid,
                                            event_id=event_id,
                                            session_id=session_id,
                                            direction=AttendanceDirection.check_in,
                                            similarity=m.get("similarity"),
                                            source="webcam_ws",
                                        )
                                    )
                                    item["attendance_logged"] = True
                                else:
                                    item["skip_reason"] = reason
                        elif m["status"] == "uncertain":
                            item["user_id"] = str(m["user_id"]) if m.get("user_id") else None
                            item["similarity"] = m.get("similarity")
                        out_faces.append(item)
                    await db.commit()
                t_match_end = time.perf_counter()
                
                await websocket.send_json({"faces": out_faces, "frame_shape": frame_shape})
                t_total = time.perf_counter() - t0
                print(
                    f"[WS DIAG] Decode: {(t_decode_end - t_decode_start)*1000:.1f}ms | "
                    f"Detect: {(t_detect_end - t_detect_start)*1000:.1f}ms | "
                    f"Match/DB: {(t_match_end - t_match_start)*1000:.1f}ms | "
                    f"Total: {t_total*1000:.1f}ms",
                    flush=True
                )
        except WebSocketDisconnect:
            return

    return app


app = create_app()
