import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Float, ForeignKey, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    admin = "admin"
    staff = "staff"
    student = "student"


class AttendanceDirection(str, enum.Enum):
    check_in = "check_in"
    check_out = "check_out"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.student)
    student_code: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    class_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    embeddings: Mapped[list["FaceEmbedding"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    attendance: Mapped[list["AttendanceLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    card_images: Mapped[list["CardImage"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    registrations: Mapped[list["EventRegistration"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def has_face(self) -> bool:
        return len(self.embeddings) > 0


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sessions: Mapped[list["EventSession"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    attendance: Mapped[list["AttendanceLog"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    registrations: Mapped[list["EventRegistration"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class EventSession(Base):
    __tablename__ = "event_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), default="default")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    event: Mapped["Event"] = relationship(back_populates="sessions")
    attendance: Mapped[list["AttendanceLog"]] = relationship(back_populates="session")


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    faiss_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    embedding_dim: Mapped[int] = mapped_column(default=512)
    model_name: Mapped[str] = mapped_column(String(64), default="buffalo_l")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    embedding_vector: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="embeddings")


class CardImage(Base):
    __tablename__ = "card_images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    image_type: Mapped[str] = mapped_column(String(32), default="front")  # "front", "back", "full_body"
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="card_images")


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event_sessions.id"), nullable=True
    )
    direction: Mapped[AttendanceDirection] = mapped_column(
        Enum(AttendanceDirection, name="attendance_direction"), nullable=False
    )
    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="webcam")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="attendance")
    event: Mapped["Event"] = relationship(back_populates="attendance")
    session: Mapped["EventSession | None"] = relationship(back_populates="attendance")


class EventRegistration(Base):
    __tablename__ = "event_registrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    event: Mapped["Event"] = relationship(back_populates="registrations")
    user: Mapped["User"] = relationship(back_populates="registrations")

