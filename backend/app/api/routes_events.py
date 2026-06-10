from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event, EventSession, EventRegistration, User
from app.db.session import get_db
from app.schemas.api import EventCreate, EventOut, SessionCreate, SessionOut, EventAssignRequest, UserOut

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventOut)
async def create_event(
    body: EventCreate,
    session: AsyncSession = Depends(get_db),
) -> Event:
    ev = Event(
        name=body.name,
        description=body.description,
        location=body.location,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        created_by=body.created_by,
    )
    session.add(ev)
    await session.commit()
    await session.refresh(ev)
    return ev


@router.get("", response_model=list[EventOut])
async def list_events(session: AsyncSession = Depends(get_db)) -> list[Event]:
    r = await session.execute(select(Event).order_by(Event.created_at.desc()))
    return list(r.scalars().all())


@router.get("/{event_id}", response_model=EventOut)
async def get_event(event_id: UUID, session: AsyncSession = Depends(get_db)) -> Event:
    ev = await session.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "Event not found")
    return ev


@router.post("/{event_id}/sessions", response_model=SessionOut)
async def open_session(
    event_id: UUID,
    body: SessionCreate,
    session: AsyncSession = Depends(get_db),
) -> EventSession:
    ev = await session.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "Event not found")
    s = EventSession(event_id=event_id, name=body.name)
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return s


@router.get("/{event_id}/sessions", response_model=list[SessionOut])
async def list_sessions(event_id: UUID, session: AsyncSession = Depends(get_db)) -> list[EventSession]:
    r = await session.execute(select(EventSession).where(EventSession.event_id == event_id))
    return list(r.scalars().all())


@router.delete("/{event_id}")
async def delete_event(event_id: UUID, session: AsyncSession = Depends(get_db)):
    ev = await session.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "Event not found")
    await session.delete(ev)
    await session.commit()
    return {"status": "ok"}


@router.post("/sessions/{session_id}/close", response_model=SessionOut)
async def close_session(session_id: UUID, session: AsyncSession = Depends(get_db)) -> EventSession:
    from sqlalchemy import func
    s = await session.get(EventSession, session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    s.closed_at = func.now()
    await session.commit()
    await session.refresh(s)
    return s


@router.post("/{event_id}/users")
async def assign_users(
    event_id: UUID,
    body: EventAssignRequest,
    session: AsyncSession = Depends(get_db),
):
    ev = await session.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "Event not found")
    
    # Remove existing registrations to avoid duplicates
    existing_q = select(EventRegistration.user_id).where(EventRegistration.event_id == event_id)
    existing_r = await session.execute(existing_q)
    existing_user_ids = set(existing_r.scalars().all())

    new_registrations = []
    for uid in body.user_ids:
        if uid not in existing_user_ids:
            reg = EventRegistration(event_id=event_id, user_id=uid)
            session.add(reg)
            new_registrations.append(reg)
            
    await session.commit()
    return {"status": "ok", "added_count": len(new_registrations)}


@router.get("/{event_id}/users", response_model=list[UserOut])
async def list_assigned_users(event_id: UUID, session: AsyncSession = Depends(get_db)) -> list[User]:
    ev = await session.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "Event not found")
    
    q = select(User).join(EventRegistration).where(EventRegistration.event_id == event_id)
    r = await session.execute(q)
    return list(r.scalars().all())


@router.delete("/{event_id}/users/{user_id}")
async def unassign_user(
    event_id: UUID,
    user_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    q = select(EventRegistration).where(
        EventRegistration.event_id == event_id,
        EventRegistration.user_id == user_id
    )
    r = await session.execute(q)
    reg = r.scalar_one_or_none()
    if not reg:
        raise HTTPException(404, "Registration not found")
    await session.delete(reg)
    await session.commit()
    return {"status": "ok"}

