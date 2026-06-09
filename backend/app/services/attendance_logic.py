from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import AttendanceDirection, AttendanceLog, FaceEmbedding
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
    """Chống duplicate: không ghi lại cùng hướng trong cửa sổ thời gian."""
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
    vote_ratio = votes[best_user] / len(hits)

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
