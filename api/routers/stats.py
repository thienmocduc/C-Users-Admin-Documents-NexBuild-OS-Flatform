"""Stats + Admin router."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.security import get_current_user, require_role
from api.models.community import AuditLog, SystemSetting
from api.models.finance import Transaction
from api.models.marketplace import Booking, Project
from api.models.order import Dispute, Escrow, Order
from api.models.product import Product
from api.models.user import User
from api.models.worker import WorkerProfile

# ─── Public Stats ─────────────────────────────────────────

stats_router = APIRouter(prefix="/stats", tags=["Stats"])


@stats_router.get("/platform")
async def platform_stats(db: AsyncSession = Depends(get_db)):
    """Stats công khai cho trang chủ (Hub)."""
    workers = (await db.execute(select(func.count(WorkerProfile.id)))).scalar() or 0
    suppliers = (await db.execute(select(func.count(User.id)).where(User.role == "supplier"))).scalar() or 0
    projects = (await db.execute(select(func.count(Project.id)))).scalar() or 0
    orders = (await db.execute(select(func.count(Order.id)))).scalar() or 0
    products = (await db.execute(select(func.count(Product.id)).where(Product.status == "published"))).scalar() or 0

    return {
        "workers": workers,
        "suppliers": suppliers,
        "projects": projects,
        "transactions": orders,
        "designs": 0,  # TODO: NexDesign AI integration
        "products": products,
    }


@stats_router.get("/admin")
async def admin_stats(
    detail: bool = False,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Admin overview + detailed analytics."""
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    gmv = (await db.execute(select(func.coalesce(func.sum(Order.total), 0)))).scalar() or 0
    escrow_held = (await db.execute(
        select(func.coalesce(func.sum(Escrow.amount), 0)).where(Escrow.status == "held")
    )).scalar() or 0

    result = {
        "total_users": total_users,
        "gmv": gmv,
        "escrow_held": escrow_held,
        "revenue": int(gmv * 0.025),  # ~2.5% commission estimate
    }

    if detail:
        # User breakdown
        for role in ["buyer", "worker", "contractor", "supplier"]:
            count = (await db.execute(select(func.count(User.id)).where(User.role == role))).scalar() or 0
            result[f"users_{role}"] = count

        # Pending approvals
        pending_products = (await db.execute(select(func.count(Product.id)).where(Product.status == "pending"))).scalar() or 0
        pending_workers = (await db.execute(select(func.count(WorkerProfile.id)).where(WorkerProfile.status == "pending"))).scalar() or 0
        open_disputes = (await db.execute(select(func.count(Dispute.id)).where(Dispute.status == "open"))).scalar() or 0

        result["pending_products"] = pending_products
        result["pending_workers"] = pending_workers
        result["open_disputes"] = open_disputes

    return result


# ─── Admin Router ─────────────────────────────────────────

admin_router = APIRouter(prefix="/admin", tags=["Admin"])


@admin_router.get("/users")
async def admin_list_users(
    role: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Quản lý users."""
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if status:
        query = query.where(User.status == status)
    if search:
        query = query.where(User.full_name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return {
        "items": [
            {"id": str(u.id), "email": u.email, "full_name": u.full_name,
             "role": u.role, "status": u.status, "created_at": u.created_at.isoformat()}
            for u in users
        ],
        "total": total, "page": page,
    }


@admin_router.patch("/users/{user_id}")
async def admin_update_user(
    user_id: UUID, req: dict,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Cập nhật user status (verify/suspend)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User không tồn tại")

    new_status = req.get("status")
    if new_status in ("active", "suspended", "rejected"):
        user.status = new_status

    db.add(AuditLog(
        user_id=current_user.id,
        event_type=f"USER_{new_status.upper()}",
        details={"target_user": str(user_id)},
        severity="action",
    ))

    return {"message": f"User đã được {new_status}", "ok": True}


@admin_router.get("/products/pending")
async def admin_pending_products(current_user=Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    """Sản phẩm chờ duyệt."""
    result = await db.execute(select(Product).where(Product.status == "pending").order_by(Product.created_at.desc()))
    products = result.scalars().all()
    return [
        {"id": str(p.id), "name": p.name, "price": p.price, "supplier_id": str(p.supplier_id), "created_at": p.created_at.isoformat()}
        for p in products
    ]


@admin_router.get("/workers/pending")
async def admin_pending_workers(current_user=Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    """Hồ sơ thợ chờ duyệt."""
    result = await db.execute(select(WorkerProfile).where(WorkerProfile.status == "pending").order_by(WorkerProfile.created_at.desc()))
    workers = result.scalars().all()
    return [
        {"id": str(w.id), "user_id": str(w.user_id), "trade": w.trade, "ai_score": w.ai_score, "created_at": w.created_at.isoformat()}
        for w in workers
    ]


@admin_router.get("/disputes")
async def admin_disputes(current_user=Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    """Danh sách khiếu nại."""
    result = await db.execute(select(Dispute).where(Dispute.status == "open").order_by(Dispute.created_at.desc()))
    disputes = result.scalars().all()
    return [
        {"id": str(d.id), "escrow_id": str(d.escrow_id), "reason": d.reason,
         "description": d.description, "status": d.status, "deadline": d.deadline.isoformat() if d.deadline else None}
        for d in disputes
    ]


@admin_router.patch("/disputes/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: UUID, req: dict,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Giải quyết khiếu nại."""
    result = await db.execute(select(Dispute).where(Dispute.id == dispute_id))
    dispute = result.scalar_one_or_none()
    if not dispute:
        raise HTTPException(404, "Khiếu nại không tồn tại")

    resolution = req.get("resolution")  # refund / release / partial
    dispute.status = f"resolved_{resolution}"
    dispute.resolution = req.get("notes")
    dispute.resolved_by = current_user.id
    from datetime import datetime, timezone
    dispute.resolved_at = datetime.now(timezone.utc)

    # Handle escrow
    escrow_r = await db.execute(select(Escrow).where(Escrow.id == dispute.escrow_id))
    escrow = escrow_r.scalar_one_or_none()
    if escrow:
        if resolution == "refund":
            escrow.status = "refunded"
        elif resolution == "release":
            escrow.status = "released"
            escrow.released_at = datetime.now(timezone.utc)

    return {"message": f"Khiếu nại đã giải quyết: {resolution}", "ok": True}


@admin_router.get("/transactions")
async def admin_transactions(
    type: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Tất cả giao dịch."""
    query = select(Transaction)
    if type:
        query = query.where(Transaction.type == type)
    query = query.order_by(Transaction.created_at.desc())

    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    txs = result.scalars().all()
    return [
        {"id": str(t.id), "user_id": str(t.user_id), "type": t.type,
         "amount": t.amount, "status": t.status, "created_at": t.created_at.isoformat()}
        for t in txs
    ]


@admin_router.get("/settings")
async def get_settings_list(current_user=Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    """Cấu hình hệ thống."""
    result = await db.execute(select(SystemSetting))
    settings = result.scalars().all()
    return {s.key: {"value": s.value, "description": s.description} for s in settings}


@admin_router.put("/settings/{key}")
async def update_setting(
    key: str, req: dict,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Sửa cấu hình."""
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(404, "Setting không tồn tại")

    setting.value = str(req.get("value", setting.value))
    setting.updated_by = current_user.id

    db.add(AuditLog(
        user_id=current_user.id,
        event_type="SETTING_CHANGED",
        details={"key": key, "value": setting.value},
        severity="action",
    ))

    return {"message": f"Đã cập nhật {key}", "ok": True}


@admin_router.get("/audit-log")
async def get_audit_log(
    event: Optional[str] = None,
    severity: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Nhật ký audit."""
    query = select(AuditLog)
    if event:
        query = query.where(AuditLog.event_type == event)
    if severity:
        query = query.where(AuditLog.severity == severity)
    query = query.order_by(AuditLog.created_at.desc())

    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    logs = result.scalars().all()
    return [
        {"id": l.id, "user_id": str(l.user_id) if l.user_id else None,
         "event_type": l.event_type, "ip_address": l.ip_address,
         "details": l.details, "severity": l.severity,
         "created_at": l.created_at.isoformat()}
        for l in logs
    ]
