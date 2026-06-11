from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import AttendanceDirection, AttendanceLog, FaceEmbedding, EventRegistration
from app.services.faiss_indexer import FaissFaceIndex


async def next_faiss_id(session: AsyncSession) -> int:
    r = await session.execute(select(FaceEmbedding.faiss_id).order_by(FaceEmbedding.faiss_id.desc()).limit(1))
    row = r.scalar_one_or_none()
    return int(row) + 1 if row is not None else 1


async def should_log_attendance(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    event_id: uuid.UUID,
    direction: AttendanceDirection,
) -> tuple[bool, str]:
    """Chống duplicate: không ghi lại cùng hướng trong cửa sổ thời gian.
    Chỉ cho phép điểm danh nếu sinh viên đã được gán vào sự kiện.
    """
    # Kiểm tra xem sinh viên có được gán (assign) vào sự kiện này không
    reg_q = select(EventRegistration).where(
        EventRegistration.event_id == event_id,
        EventRegistration.user_id == user_id
    )
    reg_r = await session.execute(reg_q)
    if not reg_r.scalar_one_or_none():
        return False, "not_assigned"

    settings = get_settings()
    window = timedelta(seconds=settings.dedupe_window_seconds)
    since = datetime.now(timezone.utc) - window
    q = (
        select(AttendanceLog)
        .where(
            AttendanceLog.user_id == user_id,
            AttendanceLog.event_id == event_id,
            AttendanceLog.direction == direction,
            AttendanceLog.created_at >= since,
        )
        .order_by(AttendanceLog.created_at.desc())
        .limit(1)
    )
    r = await session.execute(q)
    if r.scalar_one_or_none():
        return False, "dedupe_window"
    return True, "ok"



async def maybe_enrich_gallery(
    session: AsyncSession,
    faiss_index: FaissFaceIndex,
    *,
    user_id: uuid.UUID,
    embedding: Any,
    similarity: float | None,
    source: str = "webcam_ws",
) -> tuple[bool, str, int | None]:
    """Append a high-confidence real-world embedding to the gallery.

    Progressive enrichment is intentionally conservative: primary enrollment
    embeddings remain the anchor, enriched embeddings are capped by count,
    ratio, and a short per-user dedupe window.
    """
    settings = get_settings()
    if similarity is None or float(similarity) < settings.enrichment_threshold:
        return False, "below_enrichment_threshold", None

    total_q = select(func.count()).select_from(FaceEmbedding).where(FaceEmbedding.user_id == user_id)
    total = int((await session.execute(total_q)).scalar_one())
    if total <= 0:
        return False, "no_primary_gallery", None

    enriched_q = (
        select(func.count())
        .select_from(FaceEmbedding)
        .where(FaceEmbedding.user_id == user_id, FaceEmbedding.is_primary.is_(False))
    )
    enriched = int((await session.execute(enriched_q)).scalar_one())
    if enriched >= settings.enrichment_max_embeddings_per_user:
        return False, "max_enriched_embeddings", None
    if enriched / max(total, 1) >= settings.enrichment_max_ratio:
        return False, "max_enriched_ratio", None

    since = datetime.now(timezone.utc) - timedelta(seconds=settings.enrichment_dedupe_seconds)
    recent_q = (
        select(func.count())
        .select_from(FaceEmbedding)
        .where(
            FaceEmbedding.user_id == user_id,
            FaceEmbedding.is_primary.is_(False),
            FaceEmbedding.created_at >= since,
        )
    )
    recent = int((await session.execute(recent_q)).scalar_one())
    if recent > 0:
        return False, "enrichment_dedupe_window", None

    fid = await next_faiss_id(session)
    emb = np.asarray(embedding, dtype=np.float32)
    fe = FaceEmbedding(
        user_id=user_id,
        faiss_id=fid,
        embedding_dim=int(emb.size),
        embedding_vector=emb.tobytes(),
        is_primary=False,
        image_path=f"enriched:{source}",
    )
    session.add(fe)
    await session.flush()
    faiss_index.add_with_id(emb, fid, fe.id, user_id)
    return True, "ok", fid


def match_identity_with_voting(
    faiss_index: FaissFaceIndex,
    embedding: Any,
    *,
    top_k: int = 10,
    vote_threshold: float = 0.6,
) -> dict[str, Any]:
    """Match identity using voting across top-k results.

    Aggregates votes from multiple embeddings to reduce false positives.

    Args:
        faiss_index: FAISS index with face embeddings
        embedding: Query embedding
        top_k: Number of top results to consider for voting
        vote_threshold: Fraction of votes needed to confirm identity
    """
    settings = get_settings()
    hits = faiss_index.search(embedding, top_k=top_k)

    if not hits:
        return {"status": "unknown", "user_id": None, "similarity": None, "hits": []}

    from collections import Counter
    votes = Counter()
    max_sim = {}

    for hit in hits:
        if hit["similarity"] >= settings.recognition_threshold:
            uid = hit["user_id"]
            votes[uid] += 1
            if uid not in max_sim:
                max_sim[uid] = hit["similarity"]
            else:
                max_sim[uid] = max(max_sim[uid], hit["similarity"])

    if not votes:
        best = hits[0]
        sim = float(best["similarity"])
        if sim < settings.unknown_threshold:
            return {"status": "unknown", "user_id": None, "similarity": sim, "hits": hits}
        return {"status": "uncertain", "user_id": uuid.UUID(best["user_id"]), "similarity": sim, "hits": hits}

    best_user = votes.most_common(1)[0][0]
    total_votes = sum(votes.values())
    vote_ratio = votes[best_user] / total_votes if total_votes > 0 else 0

    if vote_ratio >= vote_threshold:
        return {
            "status": "known",
            "user_id": uuid.UUID(best_user),
            "similarity": max_sim[best_user],
            "hits": hits,
            "votes": votes[best_user],
            "vote_ratio": vote_ratio,
        }

    return {
        "status": "uncertain",
        "user_id": uuid.UUID(best_user),
        "similarity": max_sim[best_user],
        "hits": hits,
        "votes": votes[best_user],
        "vote_ratio": vote_ratio,
    }


def match_identity(
    faiss_index: FaissFaceIndex,
    embedding: Any,
    *,
    top_k: int = 3,
) -> dict[str, Any]:
    settings = get_settings()
    hits = faiss_index.search(embedding, top_k=top_k)
    if not hits:
        return {"status": "unknown", "user_id": None, "similarity": None, "hits": []}
    best = hits[0]
    sim = float(best["similarity"])
    if sim >= settings.recognition_threshold:
        return {
            "status": "known",
            "user_id": uuid.UUID(best["user_id"]),
            "similarity": sim,
            "hits": hits,
        }
    if sim < settings.unknown_threshold:
        return {"status": "unknown", "user_id": None, "similarity": sim, "hits": hits}
    return {"status": "uncertain", "user_id": uuid.UUID(best["user_id"]), "similarity": sim, "hits": hits}
