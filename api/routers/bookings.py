"""Bookings router — worker booking + escrow."""
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import get_settings
from api.core.database import get_db
from api.core.security import get_current_user
from api.models.marketplace import Booking
from api.models.order import Escrow
from api.models.worker import WorkerProfile

settings = get_settings()
router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", status_code=201)
async def create_booking(
    req: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Đặt thợ — tính phí + tạo escrow."""
    worker_id = req.get("worker_id")
    result = await db.execute(select(WorkerProfile).where(WorkerProfile.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(404, "Thợ không tồn tại")

    num_days = req.get("num_days", 1)
    worker_fee = (worker.daily_rate or 0) * num_days
    service_fee = int(worker_fee * settings.COMMISSION_BOOKING_PCT / 100)
    total = worker_fee + service_fee

    # Parse start_date string to date object
    start_date_raw = req.get("start_date")
    if isinstance(start_date_raw, str):
        start_date_val = date.fromisoformat(start_date_raw)
    elif start_date_raw:
        start_date_val = start_date_raw
    else:
        start_date_val = date.today()

    booking = Booking(
        buyer_id=current_user.id,
        worker_id=worker.id,
        job_description=req.get("job_description", ""),
        work_address=req.get("work_address"),
        num_days=num_days,
        start_date=start_date_val,
        shift=req.get("shift"),
        worker_fee=worker_fee,
        service_fee=service_fee,
        total=total,
    )
    db.add(booking)
    await db.flush()

    # Create escrow
    escrow = Escrow(
        idempotency_key=f"booking-{booking.id}",
        buyer_id=current_user.id,
        seller_id=worker.user_id,
        entity_type="booking",
        entity_id=booking.id,
        amount=total,
        service_fee=service_fee,
        auto_release_date=date.today() + timedelta(days=settings.ESCROW_AUTO_RELEASE_DAYS),
    )
    db.add(escrow)
    await db.flush()
    booking.escrow_id = escrow.id

    return {
        "booking_id": str(booking.id),
        "worker_fee": worker_fee,
        "service_fee": service_fee,
        "total": total,
        "escrow_id": str(escrow.id),
        "message": "Đặt lịch thành công. Thợ sẽ liên hệ trong 30 phút.",
    }


@router.get("")
async def list_bookings(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Danh sách booking (buyer xem booking của mình, worker xem booking nhận)."""
    # Get worker_id if user is worker
    worker_profile = None
    if current_user.role == "worker":
        wp = await db.execute(select(WorkerProfile).where(WorkerProfile.user_id == current_user.id))
        worker_profile = wp.scalar_one_or_none()

    query = select(Booking)
    if current_user.role == "worker" and worker_profile:
        query = query.where(Booking.worker_id == worker_profile.id)
    elif current_user.role == "admin":
        pass  # admin sees all
    else:
        query = query.where(Booking.buyer_id == current_user.id)

    if status:
        query = query.where(Booking.status == status)

    query = query.order_by(Booking.created_at.desc())
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    bookings = result.scalars().all()

    return {
        "items": [
            {
                "id": str(b.id), "buyer_id": str(b.buyer_id),
                "worker_id": str(b.worker_id),
                "job_description": b.job_description,
                "start_date": b.start_date.isoformat() if b.start_date else None,
                "num_days": b.num_days, "shift": b.shift,
                "total": b.total, "status": b.status,
                "created_at": b.created_at.isoformat(),
            }
            for b in bookings
        ],
    }


@router.patch("/{booking_id}/accept")
async def accept_booking(booking_id: UUID, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Thợ chấp nhận booking."""
    booking = await _get_booking_for_worker(booking_id, current_user, db)
    if booking.status != "pending":
        raise HTTPException(400, "Booking không ở trạng thái pending")
    booking.status = "accepted"
    return {"message": "Đã chấp nhận booking", "ok": True}


@router.patch("/{booking_id}/reject")
async def reject_booking(booking_id: UUID, req: dict, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Thợ từ chối booking."""
    booking = await _get_booking_for_worker(booking_id, current_user, db)
    if booking.status != "pending":
        raise HTTPException(400, "Booking không ở trạng thái pending")
    booking.status = "rejected"
    # Refund escrow
    if booking.escrow_id:
        escrow_r = await db.execute(select(Escrow).where(Escrow.id == booking.escrow_id))
        escrow = escrow_r.scalar_one_or_none()
        if escrow:
            escrow.status = "refunded"
    return {"message": "Đã từ chối booking", "ok": True}


@router.patch("/{booking_id}/complete")
async def complete_booking(booking_id: UUID, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Xác nhận hoàn thành → release escrow."""
    result = await db.execute(select(Booking).where(Booking.id == booking_id, Booking.buyer_id == current_user.id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(404, "Booking không tồn tại")
    booking.status = "completed"
    if booking.escrow_id:
        escrow_r = await db.execute(select(Escrow).where(Escrow.id == booking.escrow_id))
        escrow = escrow_r.scalar_one_or_none()
        if escrow and escrow.status == "held":
            escrow.status = "released"
            escrow.released_at = datetime.now(timezone.utc)
    return {"message": "Đã hoàn thành. Escrow giải phóng cho thợ.", "ok": True}


@router.patch("/{booking_id}/checkin")
async def checkin(booking_id: UUID, req: dict, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Check-in GPS."""
    booking = await _get_booking_for_worker(booking_id, current_user, db)
    booking.status = "in_progress"
    # TODO: store GPS in Redis for real-time tracking
    return {"message": "Check-in thành công", "lat": req.get("lat"), "lng": req.get("lng")}


async def _get_booking_for_worker(booking_id: UUID, current_user, db) -> Booking:
    """Helper: get booking owned by worker."""
    wp = await db.execute(select(WorkerProfile).where(WorkerProfile.user_id == current_user.id))
    worker = wp.scalar_one_or_none()
    if not worker:
        raise HTTPException(403, "Không phải thợ")
    result = await db.execute(select(Booking).where(Booking.id == booking_id, Booking.worker_id == worker.id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(404, "Booking không tồn tại")
    return booking
