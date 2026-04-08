"""Shared schemas: pagination, response wrappers."""
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    limit: int
    pages: int


class MessageResponse(BaseModel):
    message: str
    ok: bool = True


class StatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = None
