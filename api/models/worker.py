"""Worker profile + portfolio models."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from api.core.types import CUUID, StringList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base


class WorkerProfile(Base):
    __tablename__ = "worker_profiles"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    trade: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    experience_years: Mapped[int | None] = mapped_column(Integer)
    daily_rate: Mapped[int | None] = mapped_column(BigInteger)
    work_area: Mapped[str | None] = mapped_column(String(200))
    travel_radius_km: Mapped[int] = mapped_column(Integer, default=10)
    bio: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[list | None] = mapped_column(StringList)
    certificates: Mapped[list | None] = mapped_column(StringList)
    portfolio_count: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Numeric(2, 1), default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    accept_escrow: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_gps: Mapped[bool] = mapped_column(Boolean, default=False)
    accept_insurance: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_score: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(CUUID())
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    location_lat: Mapped[float | None] = mapped_column(Numeric(10, 7))
    location_lng: Mapped[float | None] = mapped_column(Numeric(10, 7))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="worker_profile")
    portfolio_items = relationship("WorkerPortfolio", back_populates="worker", lazy="selectin")


class WorkerPortfolio(Base):
    __tablename__ = "worker_portfolio"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("worker_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    images: Mapped[list | None] = mapped_column(StringList)
    rating: Mapped[float | None] = mapped_column(Numeric(2, 1))
    tags: Mapped[list | None] = mapped_column(StringList)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    worker = relationship("WorkerProfile", back_populates="portfolio_items")
