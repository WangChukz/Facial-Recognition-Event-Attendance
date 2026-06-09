import os
import uuid
import unicodedata
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CardImage, User
from app.db.session import get_db
from app.schemas.api import CardImageOut, CardImageUploadResponse

router = APIRouter(prefix="/cards", tags=["card_images"])

# Thư mục lưu ảnh thẻ
CARD_IMAGES_DIR = Path("./uploads/card_images")
CARD_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Loại ảnh thẻ được phép
ALLOWED_CARD_TYPES = ["front", "back", "full_body", "enroll"]
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}


def _remove_accents(text: str) -> str:
    """Remove Vietnamese accents: Bùi Đức Thịnh → BuiDucThinh."""
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn').replace(' ', '')


def _validate_image_file(filename: str) -> bool:
    """Kiểm tra phần mở rộng file."""
    return Path(filename).suffix in ALLOWED_EXTENSIONS


def _parse_filename(filename: str) -> tuple[str, str]:
    """Parse tên file: 'BuiDucThinh_enroll.jpg' → ('BuiDucThinh', 'enroll')."""
    name_without_ext = Path(filename).stem
    parts = name_without_ext.rsplit("_", 1)

    if len(parts) == 2:
        full_name, image_type = parts
        return full_name, image_type
    else:
        return name_without_ext, "front"


@router.post("/upload-by-name", response_model=CardImageUploadResponse)
async def upload_card_image_by_name(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> CardImageUploadResponse:
    """Upload ảnh thẻ by parsing tên file.

    Cấu trúc tên file: {full_name}_{image_type}.{ext}
    Ví dụ: BuiDucThinh_enroll.jpg, NguyenVanA_front.png

    - image_type: "front", "back", "full_body", "enroll"
    - File: JPG/PNG, tối đa 5MB
    """
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    full_name_no_accents, image_type = _parse_filename(file.filename)

    if not full_name_no_accents:
        raise HTTPException(400, "Invalid filename format")

    if image_type not in ALLOWED_CARD_TYPES:
        raise HTTPException(400, f"Invalid image_type '{image_type}'. Must be one of: {ALLOWED_CARD_TYPES}")

    if not _validate_image_file(file.filename):
        raise HTTPException(400, "File must be JPG or PNG")

    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 5MB)")

    # Tìm user bằng cách so sánh tên không dấu
    q = select(User)
    r = await session.execute(q)
    users = r.scalars().all()

    matched_user = None
    for u in users:
        if _remove_accents(u.full_name) == full_name_no_accents:
            matched_user = u
            break

    if not matched_user:
        raise HTTPException(404, f"User with name '{full_name_no_accents}' not found")

    file_ext = Path(file.filename).suffix
    unique_filename = f"{matched_user.id}_{image_type}_{uuid.uuid4()}{file_ext}"
    file_path = CARD_IMAGES_DIR / unique_filename

    with open(file_path, "wb") as f:
        f.write(data)

    card = CardImage(
        user_id=matched_user.id,
        image_type=image_type,
        image_path=str(file_path),
        original_filename=file.filename,
    )
    session.add(card)
    await session.commit()
    await session.refresh(card)

    return CardImageUploadResponse(
        id=card.id,
        user_id=card.user_id,
        image_type=card.image_type,
        image_path=card.image_path,
        uploaded_at=card.uploaded_at,
    )


@router.post("/upload", response_model=CardImageUploadResponse)
async def upload_card_image(
    user_id: uuid.UUID = Form(...),
    image_type: str = Form(default="front"),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> CardImageUploadResponse:
    """Upload ảnh thẻ cho người dùng (by user_id).

    - image_type: "front", "back", "full_body"
    - File: JPG/PNG, tối đa 5MB
    """
    u = await session.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")

    if image_type not in ALLOWED_CARD_TYPES:
        raise HTTPException(400, f"Invalid image_type. Must be one of: {ALLOWED_CARD_TYPES}")

    if not _validate_image_file(file.filename or ""):
        raise HTTPException(400, "File must be JPG or PNG")

    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 5MB)")

    file_ext = Path(file.filename or "image").suffix
    unique_filename = f"{user_id}_{image_type}_{uuid.uuid4()}{file_ext}"
    file_path = CARD_IMAGES_DIR / unique_filename

    with open(file_path, "wb") as f:
        f.write(data)

    card = CardImage(
        user_id=user_id,
        image_type=image_type,
        image_path=str(file_path),
        original_filename=file.filename,
    )
    session.add(card)
    await session.commit()
    await session.refresh(card)

    return CardImageUploadResponse(
        id=card.id,
        user_id=card.user_id,
        image_type=card.image_type,
        image_path=card.image_path,
        uploaded_at=card.uploaded_at,
    )


@router.get("/user/{user_id}", response_model=list[CardImageOut])
async def get_user_card_images(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> list[CardImageOut]:
    """Lấy tất cả ảnh thẻ của người dùng."""
    q = select(CardImage).where(CardImage.user_id == user_id).order_by(CardImage.uploaded_at.desc())
    r = await session.execute(q)
    return list(r.scalars().all())


@router.get("/{card_id}", response_model=CardImageOut)
async def get_card_image(
    card_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> CardImageOut:
    """Lấy chi tiết ảnh thẻ."""
    card = await session.get(CardImage, card_id)
    if not card:
        raise HTTPException(404, "Card image not found")
    return card


@router.delete("/{card_id}")
async def delete_card_image(
    card_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Xóa ảnh thẻ."""
    card = await session.get(CardImage, card_id)
    if not card:
        raise HTTPException(404, "Card image not found")

    if os.path.exists(card.image_path):
        os.remove(card.image_path)

    await session.delete(card)
    await session.commit()

    return {"message": "Card image deleted"}


@router.get("/download/{card_id}")
async def download_card_image(
    card_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Download ảnh thẻ."""
    from fastapi.responses import FileResponse

    card = await session.get(CardImage, card_id)
    if not card:
        raise HTTPException(404, "Card image not found")

    if not os.path.exists(card.image_path):
        raise HTTPException(404, "Image file not found")

    return FileResponse(
        path=card.image_path,
        filename=card.original_filename or "card_image.jpg",
    )
