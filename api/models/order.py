"""Cart, Order, Escrow, Dispute, Review models."""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import JSON
from api.core.types import CUUID, StringList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(CUUID(), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    order_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    buyer_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(CUUID())
    shipping_address: Mapped[str | None] = mapped_column(String(500))
    receiver_name: Mapped[str | None] = mapped_column(String(255))
    receiver_phone: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
    payment_method: Mapped[str | None] = mapped_column(String(30))
    subtotal: Mapped[int] = mapped_column(BigInteger, nullable=False)
    vat: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="processing", index=True)
    escrow_id: Mapped[uuid.UUID | None] = mapped_column(CUUID())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    items = relationship("OrderItem", back_populates="order", lazy="selectin")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(CUUID())
    product_name: Mapped[str | None] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total: Mapped[int] = mapped_column(BigInteger, nullable=False)

    order = relationship("Order", back_populates="items")


class Escrow(Base):
    __tablename__ = "escrow"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    buyer_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False, index=True)
    seller_id: Mapped[uuid.UUID | None] = mapped_column(CUUID())
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # order/booking/milestone
    entity_id: Mapped[uuid.UUID] = mapped_column(CUUID(), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    service_fee: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[str] = mapped_column(String(20), default="held", index=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    auto_release_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Dispute(Base):
    __tablename__ = "disputes"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    escrow_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("escrow.id"), nullable=False, index=True)
    reporter_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[list | None] = mapped_column(StringList)
    status: Mapped[str] = mapped_column(String(20), default="open")
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(CUUID())
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(CUUID(), nullable=False, index=True)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    criteria: Mapped[dict | None] = mapped_column(JSON)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
