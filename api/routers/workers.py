"""Workers router — profiles, portfolio, reviews."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.security import get_current_user, require_role
from api.models.order import Review
from api.models.worker import WorkerPortfolio, WorkerProfile

router = APIRouter(prefix="/workers", tags=["Workers"])


@router.get("")
async def list_workers(
    trade: Optional[str] = None,
    sort: Optional[str] = Query("rating", pattern=r"^(rating|price_asc|price_desc|online|experience)$"),
    price_range: Optional[str] = None,  # "0-300000", "300000-500000", etc.
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Danh sách thợ — public."""
    query = select(WorkerProfile).where(WorkerProfile.status.in_(["verified", "basic_verified"]))

    if trade:
        query = query.where(WorkerProfile.trade == trade)
    if price_range:
        parts = price_range.split("-")
        if len(parts) == 2:
            low, high = int(parts[0]), int(parts[1])
            if high > 0:
                query = query.where(WorkerProfile.daily_rate.between(low, high))

    # Sort
    if sort == "online":
        query = query.order_by(WorkerProfile.is_online.desc(), WorkerProfile.rating.desc())
    elif sort == "price_asc":
        query = query.order_by(WorkerProfile.daily_rate.asc())
    elif sort == "price_desc":
        query = query.order_by(WorkerProfile.daily_rate.desc())
    elif sort == "experience":
        query = query.order_by(WorkerProfile.experience_years.desc())
    else:  # rating
        query = query.order_by(WorkerProfile.rating.desc())

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    workers = result.scalars().all()

    return {
        "items": [_worker_to_dict(w) for w in workers],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/{worker_id}")
async def get_worker(worker_id: UUID, db: AsyncSession = Depends(get_db)):
    """Chi tiết profile thợ."""
    result = await db.execute(select(WorkerProfile).where(WorkerProfile.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(404, "Thợ không tồn tại")
    return _worker_to_dict(worker)


@router.post("/profile", status_code=201)
async def create_worker_profile(
    req: dict,
    current_user=Depends(require_role("worker")),
    db: AsyncSession = Depends(get_db),
):
    """Tạo hồ sơ thợ (worker only)."""
    existing = await db.execute(select(WorkerProfile).where(WorkerProfile.user_id == current_user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Hồ sơ đã tồn tại. Dùng PUT để cập nhật.")

    allowed_fields = {
        "trade", "experience_years", "daily_rate", "work_area", "travel_radius_km",
        "bio", "skills", "certificates", "accept_escrow", "allow_gps", "accept_insurance",
    }
    data = {k: v for k, v in req.items() if k in allowed_fields}
    profile = WorkerProfile(user_id=current_user.id, **data)
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    return _worker_to_dict(profile)


@router.put("/profile")
async def update_worker_profile(
    req: dict,
    current_user=Depends(require_role("worker")),
    db: AsyncSession = Depends(get_db),
):
    """Sửa hồ sơ thợ."""
    result = await db.execute(select(WorkerProfile).where(WorkerProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Chưa có hồ sơ. Tạo mới trước.")

    allowed = {
        "trade", "experience_years", "daily_rate", "work_area", "travel_radius_km",
        "bio", "skills", "certificates", "accept_escrow", "allow_gps", "accept_insurance",
    }
    for k, v in req.items():
        if k in allowed:
            setattr(profile, k, v)

    return _worker_to_dict(profile)


@router.patch("/{worker_id}/status")
async def update_worker_status(
    worker_id: UUID,
    req: dict,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Admin duyệt/từ chối hồ sơ thợ."""
    result = await db.execute(select(WorkerProfile).where(WorkerProfile.id == worker_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Hồ sơ không tồn tại")

    profile.status = req.get("status", profile.status)
    profile.verified_by = current_user.id
    from datetime import datetime, timezone
    profile.verified_at = datetime.now(timezone.utc)

    return {"message": f"Hồ sơ đã được {req.get('status')}", "ok": True}


@router.patch("/{worker_id}/online")
async def update_online_status(
    worker_id: UUID,
    req: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cập nhật trạng thái online."""
    result = await db.execute(select(WorkerProfile).where(WorkerProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Chưa có hồ sơ")
    profile.is_online = req.get("is_online", False)
    return {"is_online": profile.is_online}


# ─── Portfolio ─────────────────────────────────────────────

@router.get("/{worker_id}/portfolio")
async def get_portfolio(worker_id: UUID, db: AsyncSession = Depends(get_db)):
    """Lấy portfolio thợ."""
    result = await db.execute(
        select(WorkerPortfolio).where(WorkerPortfolio.worker_id == worker_id).order_by(WorkerPortfolio.created_at.desc())
    )
    items = result.scalars().all()
    return [
        {"id": str(p.id), "title": p.title, "description": p.description,
         "images": p.images, "rating": float(p.rating) if p.rating else None, "tags": p.tags}
        for p in items
    ]


@router.post("/{worker_id}/portfolio", status_code=201)
async def add_portfolio(
    worker_id: UUID,
    req: dict,
    current_user=Depends(require_role("worker")),
    db: AsyncSession = Depends(get_db),
):
    """Thêm dự án vào portfolio."""
    result = await db.execute(select(WorkerProfile).where(WorkerProfile.id == worker_id))
    profile = result.scalar_one_or_none()
    if not profile or profile.user_id != current_user.id:
        raise HTTPException(403, "Không có quyền")

    item = WorkerPortfolio(
        worker_id=worker_id,
        title=req.get("title"),
        description=req.get("description"),
        images=req.get("images"),
        tags=req.get("tags"),
    )
    db.add(item)
    profile.portfolio_count = (profile.portfolio_count or 0) + 1
    await db.flush()
    return {"id": str(item.id), "message": "Đã thêm vào portfolio"}


# ─── Reviews ──────────────────────────────────────────────

@router.get("/{worker_id}/reviews")
async def get_worker_reviews(worker_id: UUID, db: AsyncSession = Depends(get_db)):
    """Lấy đánh giá cho thợ."""
    result = await db.execute(
        select(Review).where(Review.target_type == "worker", Review.target_id == worker_id)
        .order_by(Review.created_at.desc())
    )
    reviews = result.scalars().all()
    return [
        {"id": str(r.id), "stars": r.stars, "criteria": r.criteria,
         "comment": r.comment, "created_at": r.created_at.isoformat()}
        for r in reviews
    ]


def _worker_to_dict(w: WorkerProfile) -> dict:
    return {
        "id": str(w.id), "user_id": str(w.user_id), "trade": w.trade,
        "experience_years": w.experience_years, "daily_rate": w.daily_rate,
        "work_area": w.work_area, "travel_radius_km": w.travel_radius_km,
        "bio": w.bio, "skills": w.skills, "rating": float(w.rating) if w.rating else 0,
        "rating_count": w.rating_count, "is_online": w.is_online,
        "accept_escrow": w.accept_escrow, "allow_gps": w.allow_gps,
        "status": w.status, "portfolio_count": w.portfolio_count,
    }
