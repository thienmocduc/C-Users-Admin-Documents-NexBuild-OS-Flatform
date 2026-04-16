"""Contractor Teams router — manage team members."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from api.core.database import get_db
from api.core.security import get_current_user, require_role
from api.models.marketplace import ContractorTeam
from api.models.user import User

router = APIRouter(prefix="/contractor/team", tags=["Contractor Teams"])


class AddTeamMemberRequest(BaseModel):
    worker_id: UUID
    role_in_team: Optional[str] = Field(None, max_length=100)
    assigned_project: Optional[UUID] = None
    monthly_salary: Optional[int] = Field(None, ge=0)


class TeamMemberResponse(BaseModel):
    id: UUID
    contractor_id: UUID
    worker_id: UUID
    worker_name: Optional[str] = None
    role_in_team: Optional[str] = None
    assigned_project: Optional[UUID] = None
    monthly_salary: Optional[int] = None
    status: str
    created_at: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[TeamMemberResponse])
async def list_team(
    status: str = Query("active", pattern=r"^(active|inactive)$"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("contractor", "admin")),
):
    """Danh sách thành viên đội thợ."""
    query = select(ContractorTeam).where(
        and_(
            ContractorTeam.contractor_id == current_user.id,
            ContractorTeam.status == status,
        )
    )
    result = await db.execute(query)
    members = result.scalars().all()

    responses = []
    for m in members:
        # Get worker name
        user = await db.execute(select(User.full_name).where(User.id == m.worker_id))
        worker_name = user.scalar_one_or_none()
        responses.append(TeamMemberResponse(
            id=m.id,
            contractor_id=m.contractor_id,
            worker_id=m.worker_id,
            worker_name=worker_name,
            role_in_team=m.role_in_team,
            assigned_project=m.assigned_project,
            monthly_salary=m.monthly_salary,
            status=m.status,
            created_at=m.created_at.isoformat(),
        ))

    return responses


@router.post("", response_model=TeamMemberResponse, status_code=201)
async def add_team_member(
    req: AddTeamMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("contractor")),
):
    """Thêm thợ vào đội."""
    # Check worker exists and is a worker
    worker = await db.execute(
        select(User).where(and_(User.id == req.worker_id, User.role == "worker"))
    )
    worker = worker.scalar_one_or_none()
    if not worker:
        raise HTTPException(404, "Thợ không tồn tại")

    # Check duplicate
    existing = await db.execute(
        select(ContractorTeam).where(
            and_(
                ContractorTeam.contractor_id == current_user.id,
                ContractorTeam.worker_id == req.worker_id,
                ContractorTeam.status == "active",
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Thợ đã trong đội")

    member = ContractorTeam(
        contractor_id=current_user.id,
        worker_id=req.worker_id,
        role_in_team=req.role_in_team,
        assigned_project=req.assigned_project,
        monthly_salary=req.monthly_salary,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    return TeamMemberResponse(
        id=member.id,
        contractor_id=member.contractor_id,
        worker_id=member.worker_id,
        worker_name=worker.full_name,
        role_in_team=member.role_in_team,
        assigned_project=member.assigned_project,
        monthly_salary=member.monthly_salary,
        status=member.status,
        created_at=member.created_at.isoformat(),
    )


@router.delete("/{member_id}")
async def remove_team_member(
    member_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("contractor")),
):
    """Xóa thợ khỏi đội."""
    result = await db.execute(
        select(ContractorTeam).where(
            and_(
                ContractorTeam.id == member_id,
                ContractorTeam.contractor_id == current_user.id,
            )
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(404, "Thành viên không tồn tại")

    member.status = "inactive"
    await db.commit()

    return {"message": "Đã xóa thành viên khỏi đội", "ok": True}
