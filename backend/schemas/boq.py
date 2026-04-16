"""BOQ (Bill of Quantities) request/response schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BOQImportRequest(BaseModel):
    manual_text: Optional[str] = Field(None, max_length=10000)
    # file_url set by upload endpoint


class BOQItemResult(BaseModel):
    category: str
    name: str
    material: Optional[str] = None
    unit: str
    quantity: float
    unit_price: int
    total_price: int


class BOQParseResponse(BaseModel):
    id: UUID
    status: str
    items: list[BOQItemResult] = []
    total: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class BOQAddToCartRequest(BaseModel):
    items: list["BOQCartItem"]


class BOQCartItem(BaseModel):
    product_name: str
    quantity: int = Field(..., ge=1)
