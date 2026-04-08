"""Projects + Bids router."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.security import get_current_user, require_role
from api.models.marketplace import Bid, Project

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("")
async def list_projects(
    type: Optional[str] = None,
    location: Optional[str] = None,
    budget: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Danh sách công trình — public."""
    query = select(Project).where(Project.status.in_(["open", "bidding"]))
    if type:
        query = query.where(Project.type == type)
    if budget:
        parts = budget.split("-")
        if len(parts) == 2:
            query = query.where(Project.budget_max >= int(parts[0]))
            if int(parts[1]) > 0:
                query = query.where(Project.budget_min <= int(parts[1]))

    query = query.order_by(Project.created_at.desc())
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    projects = result.scalars().all()

    return {
        "items": [_proj_dict(p) for p in projects],
        "total": total, "page": page,
    }


@router.get("/{project_id}")
async def get_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """Chi tiết công trình."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Công trình không tồn tại")
    project.view_count = (project.view_count or 0) + 1
    return _proj_dict(project)


@router.post("", status_code=201)
async def create_project(
    req: dict,
    current_user=Depends(require_role("buyer", "contractor")),
    db: AsyncSession = Depends(get_db),
):
    """Đăng công trình."""
    allowed = {
        "title", "type", "budget_min", "budget_max", "duration_days",
        "address", "floor_area_m2", "requirements", "work_categories",
        "bid_deadline", "payment_method", "blueprints",
    }
    data = {k: v for k, v in req.items() if k in allowed}
    project = Project(owner_id=current_user.id, **data)
    db.add(project)
    await db.flush()
    return {"id": str(project.id), "message": "Đã đăng công trình", "ok": True}


@router.put("/{project_id}")
async def update_project(
    project_id: UUID,
    req: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sửa công trình (owner only)."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project or project.owner_id != current_user.id:
        raise HTTPException(403, "Không có quyền")
    allowed = {"title", "type", "budget_min", "budget_max", "duration_days", "address", "requirements", "work_categories", "bid_deadline"}
    for k, v in req.items():
        if k in allowed:
            setattr(project, k, v)
    return {"message": "Đã cập nhật", "ok": True}


# ─── Bids ─────────────────────────────────────────────────

@router.post("/{project_id}/bids", status_code=201)
async def submit_bid(
    project_id: UUID,
    req: dict,
    current_user=Depends(require_role("contractor")),
    db: AsyncSession = Depends(get_db),
):
    """Gửi hồ sơ thầu."""
    project = await db.execute(select(Project).where(Project.id == project_id))
    if not project.scalar_one_or_none():
        raise HTTPException(404, "Công trình không tồn tại")

    bid = Bid(
        project_id=project_id,
        contractor_id=current_user.id,
        bid_price=req.get("bid_price", 0),
        price_unit=req.get("price_unit", "dong"),
        duration_value=req.get("duration_value"),
        duration_unit=req.get("duration_unit"),
        capability=req.get("capability"),
        construction_plan=req.get("construction_plan"),
    )
    db.add(bid)
    await db.flush()
    return {"bid_id": str(bid.id), "message": "Đã gửi hồ sơ thầu", "ok": True}


@router.get("/{project_id}/bids")
async def list_bids(
    project_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Xem các bid (owner hoặc admin)."""
    project = await db.execute(select(Project).where(Project.id == project_id))
    proj = project.scalar_one_or_none()
    if not proj:
        raise HTTPException(404, "Công trình không tồn tại")
    if proj.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Không có quyền")

    result = await db.execute(select(Bid).where(Bid.project_id == project_id).order_by(Bid.created_at.desc()))
    bids = result.scalars().all()

    return [
        {
            "id": str(b.id), "contractor_id": str(b.contractor_id),
            "bid_price": b.bid_price, "price_unit": b.price_unit,
            "duration_value": b.duration_value, "duration_unit": b.duration_unit,
            "capability": b.capability, "status": b.status,
            "created_at": b.created_at.isoformat(),
        }
        for b in bids
    ]


@router.patch("/{project_id}/bids/{bid_id}")
async def update_bid_status(
    project_id: UUID, bid_id: UUID,
    req: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Owner duyệt bid."""
    project = await db.execute(select(Project).where(Project.id == project_id))
    proj = project.scalar_one_or_none()
    if not proj or (proj.owner_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(403, "Không có quyền")

    bid_result = await db.execute(select(Bid).where(Bid.id == bid_id))
    bid = bid_result.scalar_one_or_none()
    if not bid:
        raise HTTPException(404, "Bid không tồn tại")

    bid.status = req.get("status", bid.status)
    return {"message": f"Bid đã được {bid.status}", "ok": True}


def _proj_dict(p: Project) -> dict:
    return {
        "id": str(p.id), "owner_id": str(p.owner_id), "title": p.title,
        "type": p.type, "budget_min": p.budget_min, "budget_max": p.budget_max,
        "duration_days": p.duration_days, "address": p.address,
        "floor_area_m2": float(p.floor_area_m2) if p.floor_area_m2 else None,
        "requirements": p.requirements, "work_categories": p.work_categories,
        "bid_deadline": p.bid_deadline.isoformat() if p.bid_deadline else None,
        "status": p.status, "view_count": p.view_count,
        "created_at": p.created_at.isoformat(),
    }
