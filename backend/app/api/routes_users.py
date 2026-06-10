from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserRole
from app.db.session import get_db
from app.schemas.api import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut)
async def create_user(body: UserCreate, session: AsyncSession = Depends(get_db)) -> User:
    r = await session.execute(select(User).where(User.email == body.email))
    if r.scalar_one_or_none():
        raise HTTPException(409, "Email already registered")
    u = User(
        email=body.email,
        full_name=body.full_name,
        role=UserRole(body.role.value),
        student_code=body.student_code,
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


@router.get("", response_model=list[UserOut])
async def list_users(session: AsyncSession = Depends(get_db)) -> list[User]:
    r = await session.execute(select(User).order_by(User.created_at.desc()))
    return list(r.scalars().all())


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: UUID, session: AsyncSession = Depends(get_db)) -> User:
    u = await session.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    return u


@router.delete("/{user_id}")
async def delete_user(
    request: Request,
    user_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    u = await session.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    
    # Set created_by = None for events created by this user to avoid ForeignKeyViolationError
    from app.db.models import Event
    q_events = select(Event).where(Event.created_by == user_id)
    r_events = await session.execute(q_events)
    for ev in r_events.scalars().all():
        ev.created_by = None
    
    # 1. Remove from DB (ORM cascade handles FaceEmbeddings, etc.)
    await session.delete(u)
    await session.commit()

    # 2. Remove from FAISS
    faiss_index = request.app.state.faiss_index
    faiss_index.remove_by_user_id(user_id)

    return {"status": "ok"}

