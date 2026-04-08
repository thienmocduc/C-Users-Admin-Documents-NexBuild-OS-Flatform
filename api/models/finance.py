"""Wallet, Transaction, Bank Account models."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.types import CUUID
from api.core.database import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    available_balance: Mapped[int] = mapped_column(BigInteger, default=0)
    escrow_held: Mapped[int] = mapped_column(BigInteger, default=0)
    b2b_credit_limit: Mapped[int] = mapped_column(BigInteger, default=0)
    b2b_credit_used: Mapped[int] = mapped_column(BigInteger, default=0)
    nxt_balance: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="wallet")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after: Mapped[int | None] = mapped_column(BigInteger)
    reference_type: Mapped[str | None] = mapped_column(String(20))
    reference_id: Mapped[uuid.UUID | None] = mapped_column(CUUID())
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False, index=True)
    bank_name: Mapped[str | None] = mapped_column(String(100))
    account_number_encrypted: Mapped[str | None] = mapped_column(String(255))  # AES-256
    account_holder: Mapped[str | None] = mapped_column(String(255))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
