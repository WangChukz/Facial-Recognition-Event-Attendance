import asyncio
import os
import sys
from pathlib import Path
from app.db.session import async_session_maker, engine
from app.db.models import User, FaceEmbedding, CardImage, AttendanceLog, EventRegistration
from sqlalchemy import delete

async def re_enroll():
    # 1. Clear database tables
    async with async_session_maker() as session:
        print("Clearing users and all related tables...")
        await session.execute(delete(AttendanceLog))
        await session.execute(delete(FaceEmbedding))
        await session.execute(delete(CardImage))
        await session.execute(delete(EventRegistration))
        await session.execute(delete(User))
        await session.commit()
    
    # 2. Clear FAISS index files if they exist
    faiss_dir = Path("./faiss_indexes")
    if faiss_dir.exists():
        print("Clearing FAISS indexes...")
        for f in faiss_dir.glob("*"):
            if f.is_file():
                try:
                    f.unlink()
                except Exception as e:
                    print(f"   Could not delete {f.name}: {e}")
                
    print("Running complete_enrollment pipeline...")
    # 3. Import and call main from complete_enrollment
    from complete_enrollment import main as enroll_main
    await enroll_main()

if __name__ == "__main__":
    asyncio.run(re_enroll())
