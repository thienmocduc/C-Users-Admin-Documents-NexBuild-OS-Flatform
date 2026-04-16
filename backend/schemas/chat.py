"""Chat request/response schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreateRoomRequest(BaseModel):
    participant_id: UUID
    entity_type: Optional[str] = None  # order/booking/project
    entity_id: Optional[UUID] = None


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    id: UUID
    room_id: UUID
    sender_id: UUID
    sender_name: Optional[str] = None
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RoomResponse(BaseModel):
    id: UUID
    type: str
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    participants: list[UUID] = []
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
