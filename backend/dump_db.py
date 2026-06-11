import asyncio
import json
import uuid
from datetime import datetime
from sqlalchemy import select
from app.db.session import async_session_maker
from app.db.models import User, Event, EventSession, FaceEmbedding, CardImage, EventRegistration, AttendanceLog

def custom_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, bytes):
        return obj.hex()
    raise TypeError(f"Type {type(obj)} not serializable")

async def dump():
    data = {}
    async with async_session_maker() as session:
        # Users
        users = (await session.execute(select(User))).scalars().all()
        data["users"] = [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "student_code": u.student_code,
                "class_name": u.class_name,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "updated_at": u.updated_at.isoformat() if u.updated_at else None,
            }
            for u in users
        ]
        
        # Events
        events = (await session.execute(select(Event))).scalars().all()
        data["events"] = [
            {
                "id": str(e.id),
                "name": e.name,
                "description": e.description,
                "location": e.location,
                "starts_at": e.starts_at.isoformat() if e.starts_at else None,
                "ends_at": e.ends_at.isoformat() if e.ends_at else None,
                "created_by": str(e.created_by) if e.created_by else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]

        # Event Sessions
        sessions = (await session.execute(select(EventSession))).scalars().all()
        data["event_sessions"] = [
            {
                "id": str(s.id),
                "event_id": str(s.event_id),
                "name": s.name,
                "opened_at": s.opened_at.isoformat() if s.opened_at else None,
                "closed_at": s.closed_at.isoformat() if s.closed_at else None,
            }
            for s in sessions
        ]

        # Face Embeddings
        embeddings = (await session.execute(select(FaceEmbedding))).scalars().all()
        data["face_embeddings"] = [
            {
                "id": str(fe.id),
                "user_id": str(fe.user_id),
                "faiss_id": fe.faiss_id,
                "embedding_dim": fe.embedding_dim,
                "model_name": fe.model_name,
                "is_primary": fe.is_primary,
                "image_path": fe.image_path,
                "embedding_vector": fe.embedding_vector.hex(),
                "created_at": fe.created_at.isoformat() if fe.created_at else None,
            }
            for fe in embeddings
        ]

        # Card Images
        card_images = (await session.execute(select(CardImage))).scalars().all()
        data["card_images"] = [
            {
                "id": str(ci.id),
                "user_id": str(ci.user_id),
                "image_type": ci.image_type,
                "image_path": ci.image_path,
                "original_filename": ci.original_filename,
                "uploaded_at": ci.uploaded_at.isoformat() if ci.uploaded_at else None,
            }
            for ci in card_images
        ]

        # Attendance Logs
        logs = (await session.execute(select(AttendanceLog))).scalars().all()
        data["attendance_logs"] = [
            {
                "id": str(l.id),
                "user_id": str(l.user_id),
                "event_id": str(l.event_id),
                "session_id": str(l.session_id) if l.session_id else None,
                "direction": l.direction,
                "similarity": l.similarity,
                "source": l.source,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]

        # Event Registrations
        registrations = (await session.execute(select(EventRegistration))).scalars().all()
        data["event_registrations"] = [
            {
                "id": str(r.id),
                "event_id": str(r.event_id),
                "user_id": str(r.user_id),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in registrations
        ]

    with open("database_dump.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Database dumped to database_dump.json successfully!")

if __name__ == "__main__":
    asyncio.run(dump())
