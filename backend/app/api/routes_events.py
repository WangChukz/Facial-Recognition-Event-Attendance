from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event, EventSession
from app.db.session import get_db
from app.schemas.api import EventCreate, EventOut, SessionCreate, SessionOut

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
