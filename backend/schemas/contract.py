"""Contract request/response schemas."""
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ContractCreateRequest(BaseModel):
    project_id: UUID
    contractor_id: UUID
    contract_value: int = Field(..., gt=0)
    duration_days: Optional[int] = Field(None, gt=0)
    warranty_months: int = Field(12, ge=0)
    late_penalty_pct: float = Field(0.1, ge=0, le=100)
    milestones: list["MilestoneInput"] = []


class MilestoneInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    percentage: int = Field(..., ge=1, le=100)
    due_date: Optional[date] = None


class SignContractRequest(BaseModel):
    otp: str = Field(..., min_length=6, max_length=6)


class ContractResponse(BaseModel):
    id: UUID
    contract_number: str
    project_id: UUID
    investor_id: UUID
    contractor_id: UUID
    contract_value: int
    duration_days: Optional[int] = None
    warranty_months: int
    late_penalty_pct: float
    milestone_count: Optional[int] = None
    signed_by_investor: bool
    signed_by_contractor: bool
    signed_at: Optional[datetime] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MilestoneResponse(BaseModel):
    id: UUID
    project_id: UUID
    contractor_id: Optional[UUID] = None
    name: Optional[str] = None
    percentage: Optional[int] = None
    amount: Optional[int] = None
    status: str
    escrow_id: Optional[UUID] = None
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
