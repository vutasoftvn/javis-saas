from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from agentos.api.db.models import Conversation, Message, MessageAttachment, RunEvent
from agentos.core.redaction import redact_payload


class ChatRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_conversation(
        self,
        *,
        company_id: str,
        workspace_id: str,
        created_by_principal: str,
        title: str = "New Conversation",
        active_agent_profile: Optional[str] = None,
    ) -> Conversation:
        conv = Conversation(
            company_id=company_id,
            workspace_id=workspace_id,
            created_by_principal=created_by_principal,
            title=title,
            active_agent_profile=active_agent_profile,
        )
        self.session.add(conv)
        self.session.commit()
        self.session.refresh(conv)
        return conv

    def get_conversation(
        self, conversation_id: str, *, company_id: str, workspace_id: str
    ) -> Optional[Conversation]:
        return (
            self.session.query(Conversation)
            .filter(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.company_id == company_id,
                    Conversation.workspace_id == workspace_id,
                )
            )
            .first()
        )

    def list_conversations(
        self,
        *,
        company_id: str,
        workspace_id: str,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        query = self.session.query(Conversation).filter(
            and_(
                Conversation.company_id == company_id,
                Conversation.workspace_id == workspace_id,
            )
        )
        if not include_archived:
            query = query.filter(Conversation.archived_at.is_(None))
        return query.order_by(desc(Conversation.updated_at)).offset(offset).limit(limit).all()

    def update_conversation(
        self,
        conversation_id: str,
        *,
        company_id: str,
        workspace_id: str,
        title: Optional[str] = None,
        active_agent_profile: Optional[str] = None,
        archived: Optional[bool] = None,
    ) -> Optional[Conversation]:
        conv = self.get_conversation(
            conversation_id, company_id=company_id, workspace_id=workspace_id
        )
        if not conv:
            return None

        if title is not None:
            conv.title = title
        if active_agent_profile is not None:
            conv.active_agent_profile = active_agent_profile
        if archived is not None:
            conv.archived_at = datetime.now(timezone.utc) if archived else None

        conv.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(conv)
        return conv

    def create_message(
        self,
        *,
        conversation_id: str,
        role: str,
        content: str,
        run_id: Optional[str] = None,
        parent_message_id: Optional[str] = None,
        status: str = "completed",
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            run_id=run_id,
            parent_message_id=parent_message_id,
            status=status,
        )
        self.session.add(msg)
        # Also touch conversation updated_at
        conv = self.session.query(Conversation).filter_by(id=conversation_id).first()
        if conv:
            conv.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(msg)
        return msg

    def list_messages(
        self,
        conversation_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Message]:
        return (
            self.session.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def create_attachment(
        self,
        *,
        message_id: str,
        object_ref: str,
        media_type: str,
        file_name: str,
        size: int = 0,
        checksum: Optional[str] = None,
        knowledge_ingest_status: str = "pending",
    ) -> MessageAttachment:
        att = MessageAttachment(
            message_id=message_id,
            object_ref=object_ref,
            media_type=media_type,
            file_name=file_name,
            size=size,
            checksum=checksum,
            knowledge_ingest_status=knowledge_ingest_status,
        )
        self.session.add(att)
        self.session.commit()
        self.session.refresh(att)
        return att

    def save_run_event(
        self,
        *,
        run_id: str,
        sequence: int,
        event_type: str,
        payload: dict[str, Any],
    ) -> RunEvent:
        # Phase 0a / Phase 4b: Must strictly redact before saving
        redacted = redact_payload(payload)
        payload_json = json.dumps(redacted, default=str)

        run_event = RunEvent(
            run_id=run_id,
            sequence=sequence,
            event_type=event_type,
            payload_redacted=payload_json,
        )
        self.session.add(run_event)
        self.session.commit()
        self.session.refresh(run_event)
        return run_event

    def get_run_events(
        self, run_id: str, *, since_sequence: Optional[int] = None
    ) -> list[RunEvent]:
        query = self.session.query(RunEvent).filter(RunEvent.run_id == run_id)
        if since_sequence is not None:
            query = query.filter(RunEvent.sequence > since_sequence)
        return query.order_by(RunEvent.sequence.asc()).all()
