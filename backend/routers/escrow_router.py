"""Escrow router — list, release, dispute."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.security import get_current_user
from api.models.order import Dispute, Escrow
from api.models.finance import Transaction, Wallet

router = APIRouter(prefix="/escrow", tags=["Escrow"])


@router.get("")
async def list_escrows(
    status: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Danh sách escrow của user (buyer hoặc seller)."""
    query = select(Escrow).where(
        or_(Escrow.buyer_id == current_user.id, Escrow.seller_id == current_user.id)
    )
    if status:
        query = query.where(Escrow.status == status)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * limit
    result = await db.execute(query.order_by(Escrow.created_at.desc()).offset(offset).limit(limit))
    escrows = result.scalars().all()

    return {
        "items": [
            {
                "id": str(e.id),
                "entity_type": e.entity_type,
                "entity_id": str(e.entity_id),
                "buyer_id": str(e.buyer_id),
                "seller_id": str(e.seller_id) if e.seller_id else None,
                "amount": e.amount,
                "service_fee": e.service_fee,
                "status": e.status,
                "auto_release_date": e.auto_release_date.isoformat() if e.auto_release_date else None,
                "created_at": e.created_at.isoformat(),
            }
            for e in escrows
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit else 0,
    }


@router.post("/{escrow_id}/release")
async def release_escrow(
    escrow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Buyer xác nhận release tiền cho seller."""
    result = await db.execute(select(Escrow).where(Escrow.id == escrow_id))
    escrow = result.scalar_one_or_none()
    if not escrow:
        raise HTTPException(404, "Escrow không tồn tại")

    if escrow.buyer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Chỉ buyer hoặc admin mới được release")

    if escrow.status != "held":
        raise HTTPException(400, f"Escrow đang ở trạng thái '{escrow.status}', không thể release")

    # Release funds to seller wallet
    escrow.status = "released"
    escrow.released_at = datetime.now(timezone.utc)

    if escrow.seller_id:
        # Credit seller wallet
        seller_wallet = await db.execute(
            select(Wallet).where(Wallet.user_id == escrow.seller_id)
        )
        wallet = seller_wallet.scalar_one_or_none()
        if wallet:
            payout = escrow.amount - escrow.service_fee
            wallet.available_balance += payout
            wallet.escrow_held -= escrow.amount

            # Record transaction
            db.add(Transaction(
                user_id=escrow.seller_id,
                type="escrow_release",
                amount=payout,
                balance_after=wallet.available_balance,
                reference_type=escrow.entity_type,
                reference_id=escrow.entity_id,
                description=f"Nhận thanh toán từ escrow #{str(escrow.id)[:8]}",
            ))

    await db.commit()
    return {"message": "Đã release escrow thành công", "ok": True}


@router.post("/{escrow_id}/dispute")
async def open_dispute(
    escrow_id: str,
    reason: str = Query(..., min_length=3, max_length=50),
    description: str = Query(None, max_length=2000),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Buyer mở dispute cho escrow."""
    result = await db.execute(select(Escrow).where(Escrow.id == escrow_id))
    escrow = result.scalar_one_or_none()
    if not escrow:
        raise HTTPException(404, "Escrow không tồn tại")

    if escrow.buyer_id != current_user.id:
        raise HTTPException(403, "Chỉ buyer mới được mở dispute")

    if escrow.status != "held":
        raise HTTPException(400, "Escrow không ở trạng thái có thể dispute")

    # Check existing dispute
    existing = await db.execute(
        select(Dispute).where(
            and_(Dispute.escrow_id == escrow_id, Dispute.status == "open")
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Đã có dispute đang mở cho escrow này")

    escrow.status = "disputed"

    dispute = Dispute(
        escrow_id=escrow_id,
        reporter_id=current_user.id,
        reason=reason,
        description=description,
        deadline=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db.add(dispute)
    await db.commit()
    await db.refresh(dispute)

    return {
        "message": "Đã mở dispute. Admin sẽ xử lý trong 48h.",
        "ok": True,
        "dispute_id": str(dispute.id),
    }
