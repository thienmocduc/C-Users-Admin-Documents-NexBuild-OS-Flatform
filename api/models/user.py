"""User + Auth models."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.types import CUUID
from api.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # buyer/worker/contractor/supplier/admin
    avatar_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending/active/suspended/rejected
    plan: Mapped[str] = mapped_column(String(20), default="free")  # free/pro/enterprise
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Supplier-specific (NULL for other roles)
    store_name: Mapped[str | None] = mapped_column(String(255))
    supplier_type: Mapped[str | None] = mapped_column(String(50))
    main_category: Mapped[str | None] = mapped_column(String(100))
    delivery_area: Mapped[str | None] = mapped_column(String(200))
    supplier_intro: Mapped[str | None] = mapped_column(Text)
    b2b_credit_policy: Mapped[str | None] = mapped_column(String(20), default="none")
    pricing_tier: Mapped[str | None] = mapped_column(String(20), default="free")
    is_verified_supplier: Mapped[bool] = mapped_column(Boolean, default=False)

    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    preferences = relationship("UserPreference", back_populates="user", uselist=False, lazy="joined")
    wallet = relationship("Wallet", back_populates="user", uselist=False, lazy="selectin")
    worker_profile = relationship("WorkerProfile", back_populates="user", uselist=False)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    lang: Mapped[str] = mapped_column(String(5), default="VI")
    theme: Mapped[str] = mapped_column(String(10), default="dark")
    daily_quota: Mapped[int] = mapped_column(Integer, default=3)
    quota_reset: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", back_populates="preferences")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
