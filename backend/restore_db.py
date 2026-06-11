import asyncio
import json
import uuid
from datetime import datetime
from sqlalchemy import select, delete
from app.db.session import async_session_maker
from app.db.models import User, Event, EventSession, FaceEmbedding, CardImage, EventRegistration, AttendanceLog

async def restore():
    with open("database_dump.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    async with async_session_maker() as session:
        # Clear existing data in reverse dependency order
        await session.execute(delete(AttendanceLog))
        await session.execute(delete(EventRegistration))
        await session.execute(delete(FaceEmbedding))
        await session.execute(delete(CardImage))
        await session.execute(delete(EventSession))
        await session.execute(delete(Event))
        await session.execute(delete(User))
        await session.commit()

        # Restore Users
        for u in data.get("users", []):
            session.add(User(
                id=uuid.UUID(u["id"]),
                email=u["email"],
                full_name=u["full_name"],
                role=u["role"],
                student_code=u["student_code"],
                class_name=u["class_name"],
                is_active=u["is_active"],
                created_at=datetime.fromisoformat(u["created_at"]) if u["created_at"] else None,
                updated_at=datetime.fromisoformat(u["updated_at"]) if u["updated_at"] else None,
            ))
        await session.commit()

        # Restore Events
        for e in data.get("events", []):
            session.add(Event(
                id=uuid.UUID(e["id"]),
                name=e["name"],
                description=e["description"],
                location=e["location"],
                starts_at=datetime.fromisoformat(e["starts_at"]) if e["starts_at"] else None,
                ends_at=datetime.fromisoformat(e["ends_at"]) if e["ends_at"] else None,
                created_by=uuid.UUID(e["created_by"]) if e["created_by"] else None,
                created_at=datetime.fromisoformat(e["created_at"]) if e["created_at"] else None,
            ))
        await session.commit()

        # Restore Event Sessions
        for s in data.get("event_sessions", []):
            session.add(EventSession(
                id=uuid.UUID(s["id"]),
                event_id=uuid.UUID(s["event_id"]),
                name=s["name"],
                opened_at=datetime.fromisoformat(s["opened_at"]) if s["opened_at"] else None,
                closed_at=datetime.fromisoformat(s["closed_at"]) if s["closed_at"] else None,
            ))
        await session.commit()

        # Restore Face Embeddings
        for fe in data.get("face_embeddings", []):
            session.add(FaceEmbedding(
                id=uuid.UUID(fe["id"]),
                user_id=uuid.UUID(fe["user_id"]),
                faiss_id=fe["faiss_id"],
                embedding_dim=fe["embedding_dim"],
                model_name=fe["model_name"],
                is_primary=fe["is_primary"],
                image_path=fe["image_path"],
                embedding_vector=bytes.fromhex(fe["embedding_vector"]),
                created_at=datetime.fromisoformat(fe["created_at"]) if fe["created_at"] else None,
            ))
        await session.commit()

        # Restore Card Images
        for ci in data.get("card_images", []):
            session.add(CardImage(
                id=uuid.UUID(ci["id"]),
                user_id=uuid.UUID(ci["user_id"]),
                image_type=ci["image_type"],
                image_path=ci["image_path"],
                original_filename=ci["original_filename"],
                uploaded_at=datetime.fromisoformat(ci["uploaded_at"]) if ci["uploaded_at"] else None,
            ))
        await session.commit()

        # Restore Attendance Logs
        for l in data.get("attendance_logs", []):
            session.add(AttendanceLog(
                id=uuid.UUID(l["id"]),
                user_id=uuid.UUID(l["user_id"]),
                event_id=uuid.UUID(l["event_id"]),
                session_id=uuid.UUID(l["session_id"]) if l["session_id"] else None,
                direction=l["direction"],
                similarity=l["similarity"],
                source=l["source"],
                created_at=datetime.fromisoformat(l["created_at"]) if l["created_at"] else None,
            ))
        await session.commit()

        # Restore Event Registrations
        for r in data.get("event_registrations", []):
            session.add(EventRegistration(
                id=uuid.UUID(r["id"]),
                event_id=uuid.UUID(r["event_id"]),
                user_id=uuid.UUID(r["user_id"]),
                created_at=datetime.fromisoformat(r["created_at"]) if r["created_at"] else None,
            ))
        await session.commit()

    print("Database restored from database_dump.json successfully!")

if __name__ == "__main__":
    asyncio.run(restore())
