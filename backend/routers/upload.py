"""Upload router — file upload and delete."""
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from api.core.config import get_settings
from api.core.security import get_current_user

router = APIRouter(prefix="/upload", tags=["Upload"])
settings = get_settings()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = set(settings.ALLOWED_IMAGE_TYPES + settings.ALLOWED_DOC_TYPES)
MAX_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024  # bytes

# Derive safe extension from MIME type (NEVER trust client filename extension)
MIME_TO_EXT = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
    "text/csv": ".csv",
}


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """Upload ảnh hoặc tài liệu. Max 10MB. Trả về URL."""
    # Validate MIME type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            400,
            f"Loại file không được phép: {file.content_type}. "
            f"Chấp nhận: {', '.join(ALLOWED_TYPES)}"
        )

    # Read and check size
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, f"File quá lớn. Tối đa {settings.MAX_UPLOAD_SIZE_MB}MB")

    # SECURITY: derive extension from MIME type, NOT from user-provided filename
    ext = MIME_TO_EXT.get(file.content_type, ".bin")
    filename = f"{uuid.uuid4().hex}{ext}"

    # Save to local filesystem (Phase 1 — S3 in Phase 2)
    filepath = UPLOAD_DIR / filename
    filepath.write_bytes(content)

    url = f"/uploads/{filename}"

    return {
        "ok": True,
        "url": url,
        "filename": filename,
        "size": len(content),
        "content_type": file.content_type,
        "uploader_id": str(current_user.id),
    }


@router.delete("/{filename}")
async def delete_file(
    filename: str,
    current_user=Depends(get_current_user),
):
    """Xóa file đã upload. Chỉ admin được xóa (Phase 1 — ownership tracking in Phase 2)."""
    # Only admin can delete files (no ownership DB yet in Phase 1)
    if current_user.role != "admin":
        raise HTTPException(403, "Chỉ admin mới được xóa file. Liên hệ quản trị viên.")

    # Sanitize filename to prevent path traversal
    safe_name = os.path.basename(filename)
    filepath = UPLOAD_DIR / safe_name

    if not filepath.exists():
        raise HTTPException(404, "File không tồn tại")

    filepath.unlink()

    return {"message": "Đã xóa file", "ok": True}
