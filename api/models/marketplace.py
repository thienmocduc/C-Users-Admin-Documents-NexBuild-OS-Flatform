"""Booking, Project, Bid, Contract, Contractor Team models."""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from api.core.types import CUUID, StringList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    buyer_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False, index=True)
    worker_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("worker_profiles.id"), nullable=False, index=True)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    work_address: Mapped[str | None] = mapped_column(String(500))
    num_days: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift: Mapped[str | None] = mapped_column(String(20))  # morning/afternoon/evening
    worker_fee: Mapped[int] = mapped_column(BigInteger, nullable=False)
    service_fee: Mapped[int] = mapped_column(BigInteger, nullable=False)
    insurance_fee: Mapped[int] = mapped_column(BigInteger, default=0)
    total: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    escrow_id: Mapped[uuid.UUID | None] = mapped_column(CUUID())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str | None] = mapped_column(String(50))
    budget_min: Mapped[int | None] = mapped_column(BigInteger)
    budget_max: Mapped[int | None] = mapped_column(BigInteger)
    duration_days: Mapped[int | None] = mapped_column(Integer)
    address: Mapped[str | None] = mapped_column(String(500))
    floor_area_m2: Mapped[float | None] = mapped_column(Numeric(10, 2))
    requirements: Mapped[str | None] = mapped_column(Text)
    work_categories: Mapped[list | None] = mapped_column(StringList)
    bid_deadline: Mapped[date | None] = mapped_column(Date)
    payment_method: Mapped[str | None] = mapped_column(String(30))
    blueprints: Mapped[list | None] = mapped_column(StringList)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    bids = relationship("Bid", back_populates="project", lazy="selectin")
    milestones = relationship("ProjectMilestone", back_populates="project", lazy="selectin")


class Bid(Base):
    __tablename__ = "bids"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("projects.id"), nullable=False, index=True)
    contractor_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False, index=True)
    bid_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price_unit: Mapped[str] = mapped_column(String(10), default="dong")
    duration_value: Mapped[int | None] = mapped_column(Integer)
    duration_unit: Mapped[str | None] = mapped_column(String(10))
    capability: Mapped[str | None] = mapped_column(Text)
    construction_plan: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="bids")


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("projects.id"), nullable=False, index=True)
    contractor_id: Mapped[uuid.UUID | None] = mapped_column(CUUID())
    name: Mapped[str | None] = mapped_column(String(255))
    percentage: Mapped[int | None] = mapped_column(Integer)
    amount: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    escrow_id: Mapped[uuid.UUID | None] = mapped_column(CUUID())
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project = relationship("Project", back_populates="milestones")


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    contract_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("projects.id"), nullable=False, index=True)
    investor_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False)
    contractor_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False)
    contract_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_days: Mapped[int | None] = mapped_column(Integer)
    warranty_months: Mapped[int] = mapped_column(Integer, default=12)
    late_penalty_pct: Mapped[float] = mapped_column(Numeric(4, 2), default=0.1)
    milestone_count: Mapped[int | None] = mapped_column(Integer)
    signed_by_investor: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_by_contractor: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ContractorTeam(Base):
    __tablename__ = "contractor_teams"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    contractor_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False, index=True)
    worker_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False)
    role_in_team: Mapped[str | None] = mapped_column(String(100))
    assigned_project: Mapped[uuid.UUID | None] = mapped_column(CUUID())
    monthly_salary: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
