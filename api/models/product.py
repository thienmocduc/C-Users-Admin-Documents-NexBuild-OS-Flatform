"""Product + Category models."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from api.core.types import CUUID, StringList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(20))
    parent_id: Mapped[int | None] = mapped_column(Integer, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    promo_price: Mapped[int | None] = mapped_column(BigInteger)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    min_order: Mapped[int] = mapped_column(Integer, default=1)
    delivery_time: Mapped[str | None] = mapped_column(String(50))
    sku: Mapped[str | None] = mapped_column(String(50))
    images: Mapped[list | None] = mapped_column(StringList)
    badges: Mapped[list | None] = mapped_column(StringList)
    sale_label: Mapped[str | None] = mapped_column(String(50))
    rating: Mapped[float] = mapped_column(Numeric(2, 1), default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    is_d2c: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_b2b_credit: Mapped[bool] = mapped_column(Boolean, default=False)
    show_in_boq: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(CUUID())
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    category = relationship("Category", back_populates="products")
