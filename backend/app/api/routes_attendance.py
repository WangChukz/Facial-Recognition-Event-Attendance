from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AttendanceDirection, AttendanceLog, User, EventRegistration
from app.db.session import get_db
from app.schemas.api import AttendanceCheckInRequest, AttendanceLogOut

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("/history", response_model=list[AttendanceLogOut])
async def attendance_history(
    event_id: UUID | None = None,
    user_id: UUID | None = None,
    limit: int = 200,
    session: AsyncSession = Depends(get_db),
) -> list[AttendanceLog]:
    q = select(AttendanceLog).order_by(AttendanceLog.created_at.desc()).limit(min(limit, 1000))
    if event_id:
        q = q.where(AttendanceLog.event_id == event_id)
    if user_id:
        q = q.where(AttendanceLog.user_id == user_id)
    r = await session.execute(q)
    return list(r.scalars().all())


@router.post("/check-in", response_model=AttendanceLogOut)
async def check_in(
    body: AttendanceCheckInRequest,
    session: AsyncSession = Depends(get_db),
) -> AttendanceLog:
    u = await session.get(User, body.user_id)
    if not u:
        raise HTTPException(404, "User not found")
    
    # Kiểm tra xem sinh viên đã được gán vào sự kiện chưa
    reg_q = select(EventRegistration).where(
        EventRegistration.event_id == body.event_id,
        EventRegistration.user_id == body.user_id
    )
    reg_r = await session.execute(reg_q)
    if not reg_r.scalar_one_or_none():
        raise HTTPException(400, "Sinh viên chưa được gán vào sự kiện này")

    log = AttendanceLog(
        user_id=body.user_id,
        event_id=body.event_id,
        session_id=body.session_id,
        direction=AttendanceDirection.check_in,
        similarity=body.similarity,
        source=body.source,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


@router.post("/check-out", response_model=AttendanceLogOut)
async def check_out(
    body: AttendanceCheckInRequest,
    session: AsyncSession = Depends(get_db),
) -> AttendanceLog:
    u = await session.get(User, body.user_id)
    if not u:
        raise HTTPException(404, "User not found")
        
    # Kiểm tra xem sinh viên đã được gán vào sự kiện chưa
    reg_q = select(EventRegistration).where(
        EventRegistration.event_id == body.event_id,
        EventRegistration.user_id == body.user_id
    )
    reg_r = await session.execute(reg_q)
    if not reg_r.scalar_one_or_none():
        raise HTTPException(400, "Sinh viên chưa được gán vào sự kiện này")

    log = AttendanceLog(
        user_id=body.user_id,
        event_id=body.event_id,
        session_id=body.session_id,
        direction=AttendanceDirection.check_out,
        similarity=body.similarity,
        source=body.source,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log

