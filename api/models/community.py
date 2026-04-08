"""Forum, Chat, Notification, Audit, Settings, BOQ models."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import JSON
from api.core.types import CUUID, StringList
from sqlalchemy.orm import Mapped, mapped_column

from api.core.database import Base


# ─── Forum ────────────────────────────────────────────────

class ForumPost(Base):
    __tablename__ = "forum_posts"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list | None] = mapped_column(StringList)
    votes: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ForumComment(Base):
    __tablename__ = "forum_comments"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("forum_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ─── Chat ─────────────────────────────────────────────────

class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(20), default="direct")
    entity_type: Mapped[str | None] = mapped_column(String(20))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(CUUID())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ChatParticipant(Base):
    __tablename__ = "chat_participants"

    room_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("chat_rooms.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), primary_key=True)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("chat_rooms.id"), nullable=False, index=True)
    sender_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ─── Notifications ────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(CUUID(), ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str | None] = mapped_column(String(50))
    title: Mapped[str | None] = mapped_column(String(255))
    message: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ─── Admin ────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(CUUID(), ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45))  # Use String instead of INET for compatibility
    details: Mapped[dict | None] = mapped_column(JSON)
    severity: Mapped[str] = mapped_column(String(10), default="info")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(CUUID())


# ─── BOQ ──────────────────────────────────────────────────

class BOQImport(Base):
    __tablename__ = "boq_imports"

    id: Mapped[uuid.UUID] = mapped_column(CUUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(CUUID(), nullable=False, index=True)
    file_url: Mapped[str | None] = mapped_column(Text)
    manual_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="processing")
    result: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
