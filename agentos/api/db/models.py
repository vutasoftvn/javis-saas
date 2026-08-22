from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    company_id = Column(String(64), nullable=False, index=True)
    workspace_id = Column(String(64), nullable=False, index=True)
    created_by_principal = Column(String(128), nullable=False)
    title = Column(String(255), nullable=False, default="New Conversation")
    active_agent_profile = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    archived_at = Column(DateTime(timezone=True), nullable=True, index=True)

    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )

    __table_args__ = (
        Index("idx_conversations_workspace_archived", "workspace_id", "archived_at"),
        Index("idx_conversations_company_archived", "company_id", "archived_at"),
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    conversation_id = Column(
        String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(String(32), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False, default="")
    run_id = Column(String(64), nullable=True, index=True)
    parent_message_id = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="completed")  # started, completed, failed
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)

    conversation = relationship("Conversation", back_populates="messages")
    attachments = relationship(
        "MessageAttachment", back_populates="message", cascade="all, delete-orphan"
    )


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    message_id = Column(
        String(64), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    object_ref = Column(String(512), nullable=False)  # reference to object storage
    media_type = Column(String(128), nullable=False)
    file_name = Column(String(255), nullable=False)
    size = Column(BigInteger, nullable=False, default=0)
    checksum = Column(String(128), nullable=True)
    knowledge_ingest_status = Column(String(32), nullable=False, default="pending")  # pending, ingested, failed

    message = relationship("Message", back_populates="attachments")


class RunEvent(Base):
    __tablename__ = "run_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    event_type = Column(String(64), nullable=False)
    payload_redacted = Column(Text, nullable=False)  # JSON-encoded string, redacted
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)

    __table_args__ = (
        Index("idx_run_events_run_id_sequence", "run_id", "sequence", unique=True),
    )
