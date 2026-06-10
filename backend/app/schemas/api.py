from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models import AttendanceDirection


class UserRoleEnum(str, Enum):
    admin = "admin"
    staff = "staff"
    student = "student"


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRoleEnum = UserRoleEnum.student
    student_code: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: str
    student_code: str | None
    is_active: bool
    created_at: datetime


class EventCreate(BaseModel):
    name: str
    description: str | None = None
    location: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    created_by: UUID | None = None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    location: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    created_by: UUID | None
    created_at: datetime


class SessionCreate(BaseModel):
    name: str = "default"


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    name: str
    opened_at: datetime
    closed_at: datetime | None


class FaceRegisterResponse(BaseModel):
    user_id: UUID
    embedding_id: UUID
    faiss_id: int
    det_score: float


class AttendanceCheckInRequest(BaseModel):
    user_id: UUID
    event_id: UUID
    session_id: UUID | None = None
    similarity: float | None = None
    source: str = "manual"


class AttendanceLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    event_id: UUID
    session_id: UUID | None
    direction: AttendanceDirection
    similarity: float | None
    source: str
    created_at: datetime


class RecognitionFaceOut(BaseModel):
    bbox: list[int]
    det_score: float
    status: str
    user_id: UUID | None = None
    similarity: float | None = None
    full_name: str | None = None


class FrameRecognitionResponse(BaseModel):
    faces: list[RecognitionFaceOut]
    frame_shape: list[int] = Field(default_factory=list)


class CardImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    image_type: str
    image_path: str
    original_filename: str | None
    uploaded_at: datetime


class CardImageUploadResponse(BaseModel):
    id: UUID
    user_id: UUID
    image_type: str
    image_path: str
    uploaded_at: datetime


class EventAssignRequest(BaseModel):
    user_ids: list[UUID]

