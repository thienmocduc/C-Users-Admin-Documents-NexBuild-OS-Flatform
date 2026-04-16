"""Contracts router — create, get, sign, milestones."""
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.security import get_current_user
from api.models.marketplace import Bid, Contract, Project, ProjectMilestone
from api.schemas.contract import (
    ContractCreateRequest,
    ContractResponse,
    MilestoneResponse,
    SignContractRequest,
)

router = APIRouter(prefix="/contracts", tags=["Contracts"])


def _gen_contract_number() -> str:
    return f"NXC-{datetime.now(timezone.utc).strftime('%Y')}-{secrets.randbelow(9000) + 1000}"


@router.post("", response_model=ContractResponse, status_code=201)
async def create_contract(
    req: ContractCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Tạo hợp đồng từ dự án đã chấp nhận bid."""
    # Verify project ownership
    project = await db.execute(select(Project).where(Project.id == req.project_id))
    project = project.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Dự án không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(403, "Bạn không phải chủ dự án")

    # Validate milestone percentages sum to 100
    if req.milestones:
        total_pct = sum(m.percentage for m in req.milestones)
        if total_pct != 100:
            raise HTTPException(400, f"Tổng % milestone phải = 100 (hiện tại: {total_pct})")

    contract = Contract(
        contract_number=_gen_contract_number(),
        project_id=req.project_id,
        investor_id=current_user.id,
        contractor_id=req.contractor_id,
        contract_value=req.contract_value,
        duration_days=req.duration_days,
        warranty_months=req.warranty_months,
        late_penalty_pct=req.late_penalty_pct,
        milestone_count=len(req.milestones) if req.milestones else None,
    )
    db.add(contract)
    await db.flush()

    # Create milestones
    for m in req.milestones:
        milestone = ProjectMilestone(
            project_id=req.project_id,
            contractor_id=req.contractor_id,
            name=m.name,
            percentage=m.percentage,
            amount=int(req.contract_value * m.percentage / 100),
            due_date=m.due_date,
        )
        db.add(milestone)

    # Update project status
    project.status = "contracted"
    await db.commit()
    await db.refresh(contract)

    return ContractResponse.model_validate(contract)


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Chi tiết hợp đồng."""
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(404, "Hợp đồng không tồn tại")

    # IDOR: only investor or contractor can view
    if current_user.id not in (contract.investor_id, contract.contractor_id) and current_user.role != "admin":
        raise HTTPException(403, "Không có quyền xem hợp đồng này")

    return ContractResponse.model_validate(contract)


@router.patch("/{contract_id}/sign", response_model=ContractResponse)
async def sign_contract(
    contract_id: str,
    req: SignContractRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Ký hợp đồng (investor hoặc contractor). OTP required."""
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(404, "Hợp đồng không tồn tại")

    if contract.status not in ("draft", "pending"):
        raise HTTPException(400, "Hợp đồng không ở trạng thái có thể ký")

    # TODO: Verify OTP in production (Phase 2 — real SMS OTP)
    # For Phase 1 MVP: accept any 6-digit OTP
    if len(req.otp) != 6 or not req.otp.isdigit():
        raise HTTPException(400, "OTP không hợp lệ")

    if current_user.id == contract.investor_id:
        contract.signed_by_investor = True
    elif current_user.id == contract.contractor_id:
        contract.signed_by_contractor = True
    else:
        raise HTTPException(403, "Bạn không phải bên ký hợp đồng")

    # If both signed → activate
    if contract.signed_by_investor and contract.signed_by_contractor:
        contract.status = "active"
        contract.signed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(contract)

    return ContractResponse.model_validate(contract)


@router.get("/{contract_id}/milestones", response_model=list[MilestoneResponse])
async def get_milestones(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Danh sách milestone của hợp đồng."""
    contract = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = contract.scalar_one_or_none()
    if not contract:
        raise HTTPException(404, "Hợp đồng không tồn tại")

    if current_user.id not in (contract.investor_id, contract.contractor_id) and current_user.role != "admin":
        raise HTTPException(403, "Không có quyền xem")

    result = await db.execute(
        select(ProjectMilestone).where(ProjectMilestone.project_id == contract.project_id)
    )
    milestones = result.scalars().all()

    return [MilestoneResponse.model_validate(m) for m in milestones]
