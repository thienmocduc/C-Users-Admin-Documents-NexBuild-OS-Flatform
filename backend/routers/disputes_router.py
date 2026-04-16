"""Disputes router — user-facing list, detail, create."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from api.core.database import get_db
from api.core.security import get_current_user
from api.models.order import Dispute, Escrow

router = APIRouter(prefix="/disputes", tags=["Disputes"])


class DisputeCreateRequest(BaseModel):
    escrow_id: UUID
    reason: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = Field(None, max_length=2000)
    evidence: list[str] = []


class DisputeResponse(BaseModel):
    id: UUID
    escrow_id: UUID
    reporter_id: UUID
    reason: str
    description: Optional[str] = None
    evidence: list[str] = []
    status: str
    resolution: Optional[str] = None
    resolved_by: Optional[UUID] = None
    deadline: Optional[str] = None
    created_at: str
    resolved_at: Optional[str] = None

    model_config = {"from_attributes": True}


@router.get("")
async def list_my_disputes(
    status: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Danh sách dispute của user."""
    query = select(Dispute).where(Dispute.reporter_id == current_user.id)
    if status:
        query = query.where(Dispute.status == status)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * limit
    result = await db.execute(query.order_by(Dispute.created_at.desc()).offset(offset).limit(limit))
    disputes = result.scalars().all()

    return {
        "items": [
            {
                "id": str(d.id),
                "escrow_id": str(d.escrow_id),
                "reason": d.reason,
                "status": d.status,
                "deadline": d.deadline.isoformat() if d.deadline else None,
                "created_at": d.created_at.isoformat(),
                "resolved_at": d.resolved_at.isoformat() if d.resolved_at else None,
            }
            for d in disputes
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit else 0,
    }


@router.get("/{dispute_id}")
async def get_dispute(
    dispute_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Chi tiết dispute."""
    result = await db.execute(select(Dispute).where(Dispute.id == dispute_id))
    dispute = result.scalar_one_or_none()
    if not dispute:
        raise HTTPException(404, "Dispute không tồn tại")

    # IDOR check
    if dispute.reporter_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Không có quyền xem dispute này")

    # Get escrow info
    escrow = await db.execute(select(Escrow).where(Escrow.id == dispute.escrow_id))
    escrow = escrow.scalar_one_or_none()

    return {
        "id": str(dispute.id),
        "escrow_id": str(dispute.escrow_id),
        "reporter_id": str(dispute.reporter_id),
        "reason": dispute.reason,
        "description": dispute.description,
        "evidence": dispute.evidence or [],
        "status": dispute.status,
        "resolution": dispute.resolution,
        "resolved_by": str(dispute.resolved_by) if dispute.resolved_by else None,
        "deadline": dispute.deadline.isoformat() if dispute.deadline else None,
        "created_at": dispute.created_at.isoformat(),
        "resolved_at": dispute.resolved_at.isoformat() if dispute.resolved_at else None,
        "escrow": {
            "entity_type": escrow.entity_type,
            "entity_id": str(escrow.entity_id),
            "amount": escrow.amount,
            "status": escrow.status,
        } if escrow else None,
    }


@router.post("", status_code=201)
async def create_dispute(
    req: DisputeCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Tạo dispute mới."""
    # Verify escrow exists and user is buyer
    escrow = await db.execute(select(Escrow).where(Escrow.id == req.escrow_id))
    escrow = escrow.scalar_one_or_none()
    if not escrow:
        raise HTTPException(404, "Escrow không tồn tại")

    if escrow.buyer_id != current_user.id:
        raise HTTPException(403, "Chỉ buyer mới được tạo dispute")

    if escrow.status != "held":
        raise HTTPException(400, "Escrow không ở trạng thái có thể dispute")

    # Check existing open dispute
    existing = await db.execute(
        select(Dispute).where(
            and_(Dispute.escrow_id == req.escrow_id, Dispute.status == "open")
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Đã có dispute đang mở cho escrow này")

    escrow.status = "disputed"

    dispute = Dispute(
        escrow_id=req.escrow_id,
        reporter_id=current_user.id,
        reason=req.reason,
        description=req.description,
        evidence=req.evidence,
        deadline=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db.add(dispute)
    await db.commit()
    await db.refresh(dispute)

    return {
        "message": "Dispute đã được tạo. Admin sẽ xử lý trong 48h.",
        "ok": True,
        "id": str(dispute.id),
    }
