"""Product + Category schemas."""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    icon: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: int = 0

    model_config = {"from_attributes": True}


class ProductCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    category_id: Optional[int] = None
    price: int = Field(..., gt=0)
    promo_price: Optional[int] = Field(None, gt=0)
    unit: str = Field(..., pattern=r"^(bao|kg|tan|m2|m3|cai|bo|cuon|thung)$")
    stock: int = Field(0, ge=0)
    min_order: int = Field(1, ge=1)
    delivery_time: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    images: Optional[list[str]] = Field(None, max_length=8)
    badges: Optional[list[str]] = None
    sale_label: Optional[str] = None
    is_d2c: bool = False
    allow_b2b_credit: bool = False
    show_in_boq: bool = True


class ProductUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    category_id: Optional[int] = None
    price: Optional[int] = Field(None, gt=0)
    promo_price: Optional[int] = None
    unit: Optional[str] = None
    stock: Optional[int] = Field(None, ge=0)
    min_order: Optional[int] = Field(None, ge=1)
    delivery_time: Optional[str] = None
    description: Optional[str] = None
    images: Optional[list[str]] = None
    badges: Optional[list[str]] = None
    is_d2c: Optional[bool] = None
    allow_b2b_credit: Optional[bool] = None


class ProductResponse(BaseModel):
    id: UUID
    supplier_id: UUID
    category_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: int
    promo_price: Optional[int] = None
    unit: str
    stock: int
    min_order: int
    delivery_time: Optional[str] = None
    sku: Optional[str] = None
    images: Optional[list[str]] = None
    badges: Optional[list[str]] = None
    sale_label: Optional[str] = None
    rating: float = 0
    rating_count: int = 0
    is_d2c: bool
    status: str

    model_config = {"from_attributes": True}


class ProductStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(published|rejected)$")
    reason: Optional[str] = None
