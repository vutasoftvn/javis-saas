from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional, Protocol, runtime_checkable

from sqlalchemy import text

from agent_core.conversations.models import (
    ConversationRecord,
    MessageAttachmentRecord,
    MessageRecord,
)

__all__ = [
    "ConversationRepository",
    "InMemoryConversationRepository",
    "PostgresConversationRepository",
]


@runtime_checkable
class ConversationRepository(Protocol):
    """Protocol cho Durable Conversation Substrate — thay thế in-memory globals
    (_conversations/_messages/_pending_runs) tại apps/cosa/api/routes.py.
    """

    async def create_conversation(self, conversation: ConversationRecord) -> ConversationRecord: ...
    async def get_conversation(self, conversation_id: str) -> Optional[ConversationRecord]: ...
    async def get_scoped_conversation(
        self, workspace_id: str, conversation_id: str
    ) -> Optional[ConversationRecord]: ...
    async def list_conversations(
        self,
        *,
        workspace_id: str,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ConversationRecord], int]: ...
    async def update_conversation(
        self,
        conversation_id: str,
        *,
        title: Optional[str] = None,
        active_agent_profile: Optional[str] = None,
        archived: Optional[bool] = None,
    ) -> Optional[ConversationRecord]: ...

    async def add_message(
        self,
        message: MessageRecord,
        attachments: Optional[list[MessageAttachmentRecord]] = None,
    ) -> MessageRecord: ...
    async def list_messages(self, conversation_id: str) -> list[MessageRecord]: ...


class InMemoryConversationRepository:
    """In-memory implementation dùng cho unit test và local dev nhanh — không dùng production."""

    def __init__(self) -> None:
        self._conversations: dict[str, ConversationRecord] = {}
        self._messages: dict[str, list[MessageRecord]] = {}
        self._seq_counters: dict[str, int] = {}

    async def create_conversation(self, conversation: ConversationRecord) -> ConversationRecord:
        self._conversations[conversation.conversation_id] = conversation.model_copy(deep=True)
        self._messages[conversation.conversation_id] = []
        return conversation

    async def get_conversation(self, conversation_id: str) -> Optional[ConversationRecord]:
        conv = self._conversations.get(conversation_id)
        return conv.model_copy(deep=True) if conv else None

    async def get_scoped_conversation(
        self, workspace_id: str, conversation_id: str
    ) -> Optional[ConversationRecord]:
        conv = self._conversations.get(conversation_id)
        if conv and conv.workspace_id == workspace_id:
            return conv.model_copy(deep=True)
        return None


    async def list_conversations(
        self,
        *,
        workspace_id: str,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ConversationRecord], int]:
        items = [
            c for c in self._conversations.values()
            if (include_archived or c.archived_at is None)
            and (c.workspace_id == workspace_id)
        ]
        items.sort(key=lambda c: c.created_at, reverse=True)
        total = len(items)
        return [c.model_copy(deep=True) for c in items[offset : offset + limit]], total

    async def update_conversation(
        self,
        conversation_id: str,
        *,
        title: Optional[str] = None,
        active_agent_profile: Optional[str] = None,
        archived: Optional[bool] = None,
    ) -> Optional[ConversationRecord]:
        conv = self._conversations.get(conversation_id)
        if not conv:
            return None
        if title is not None:
            conv.title = title
        if active_agent_profile is not None:
            conv.active_agent_profile = active_agent_profile
        if archived is not None:
            conv.archived_at = datetime.now(timezone.utc) if archived else None
        conv.updated_at = datetime.now(timezone.utc)
        return conv.model_copy(deep=True)

    async def add_message(
        self,
        message: MessageRecord,
        attachments: Optional[list[MessageAttachmentRecord]] = None,
    ) -> MessageRecord:
        stored = message.model_copy(deep=True)
        stored.attachments = list(attachments or [])
        seq = self._seq_counters.get(message.conversation_id, 0) + 1
        self._seq_counters[message.conversation_id] = seq
        stored.sequence_no = seq
        self._messages.setdefault(message.conversation_id, []).append(stored)
        return stored.model_copy(deep=True)

    async def list_messages(self, conversation_id: str) -> list[MessageRecord]:
        msgs = self._messages.get(conversation_id, [])
        return [m.model_copy(deep=True) for m in msgs]


class PostgresConversationRepository:
    """PostgreSQL implementation persisting to agent_conversation.* schema (migration 006)."""

    def __init__(self, db_session_factory: Any) -> None:
        if db_session_factory is None:
            raise ValueError("PostgresConversationRepository requires a valid db_session_factory.")
        self._session_factory = db_session_factory

    async def create_conversation(self, conversation: ConversationRecord) -> ConversationRecord:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_conversation.conversations (
                        conversation_id, workspace_id, created_by_principal,
                        title, active_agent_profile, metadata, created_at, updated_at, archived_at
                    ) VALUES (
                        :conversation_id, :workspace_id, :created_by_principal,
                        :title, :active_agent_profile, :metadata, :created_at, :updated_at, :archived_at
                    )
                    """
                ),
                {
                    "conversation_id": conversation.conversation_id,
                    "workspace_id": conversation.workspace_id,
                    "created_by_principal": conversation.created_by_principal,
                    "title": conversation.title,
                    "active_agent_profile": conversation.active_agent_profile,
                    "metadata": json.dumps(conversation.metadata),
                    "created_at": conversation.created_at,
                    "updated_at": conversation.updated_at,
                    "archived_at": conversation.archived_at,
                },
            )
            await session.commit()
        return conversation

    async def get_conversation(self, conversation_id: str) -> Optional[ConversationRecord]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT conversation_id, workspace_id, created_by_principal,
                           title, active_agent_profile, metadata, created_at, updated_at, archived_at
                    FROM agent_conversation.conversations
                    WHERE conversation_id = :conversation_id
                    """
                ),
                {"conversation_id": conversation_id},
            )
            row = res.mappings().first()
            return self._row_to_conversation(row) if row else None

    async def get_scoped_conversation(
        self, workspace_id: str, conversation_id: str
    ) -> Optional[ConversationRecord]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT conversation_id, workspace_id, created_by_principal,
                           title, active_agent_profile, metadata, created_at, updated_at, archived_at
                    FROM agent_conversation.conversations
                    WHERE conversation_id = :conversation_id
                      AND workspace_id = :workspace_id
                    """
                ),
                {
                    "conversation_id": conversation_id,
                    "workspace_id": workspace_id,
                },
            )
            row = res.mappings().first()
            return self._row_to_conversation(row) if row else None


    async def list_conversations(
        self,
        *,
        workspace_id: str,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ConversationRecord], int]:
        clauses = ["workspace_id = :workspace_id"]
        if not include_archived:
            clauses.append("archived_at IS NULL")
        params: dict[str, Any] = {"workspace_id": workspace_id, "limit": limit, "offset": offset}
        where_clause = f"WHERE {' AND '.join(clauses)}"

        async with self._session_factory() as session:
            count_res = await session.execute(
                text(f"SELECT COUNT(*) AS total FROM agent_conversation.conversations {where_clause}"),
                {k: v for k, v in params.items() if k not in ("limit", "offset")},
            )
            total = int(count_res.mappings().first()["total"])

            res = await session.execute(
                text(
                    f"""
                    SELECT conversation_id, workspace_id, created_by_principal,
                           title, active_agent_profile, metadata, created_at, updated_at, archived_at
                    FROM agent_conversation.conversations
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            )
            rows = res.mappings().all()
            return [self._row_to_conversation(r) for r in rows], total

    async def update_conversation(
        self,
        conversation_id: str,
        *,
        title: Optional[str] = None,
        active_agent_profile: Optional[str] = None,
        archived: Optional[bool] = None,
    ) -> Optional[ConversationRecord]:
        now = datetime.now(timezone.utc)
        archived_at: Optional[datetime] = (now if archived else None) if archived is not None else None

        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    UPDATE agent_conversation.conversations
                    SET title = COALESCE(:title, title),
                        active_agent_profile = COALESCE(:active_agent_profile, active_agent_profile),
                        archived_at = CASE WHEN :archived_set THEN :archived_at ELSE archived_at END,
                        updated_at = :updated_at
                    WHERE conversation_id = :conversation_id
                    """
                ),
                {
                    "conversation_id": conversation_id,
                    "title": title,
                    "active_agent_profile": active_agent_profile,
                    "archived_set": archived is not None,
                    "archived_at": archived_at,
                    "updated_at": now,
                },
            )
            await session.commit()
        return await self.get_conversation(conversation_id)

    async def add_message(
        self,
        message: MessageRecord,
        attachments: Optional[list[MessageAttachmentRecord]] = None,
    ) -> MessageRecord:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    INSERT INTO agent_conversation.messages (
                        message_id, conversation_id, role, content, run_id, parent_message_id,
                        status, created_at
                    ) VALUES (
                        :message_id, :conversation_id, :role, :content, :run_id, :parent_message_id,
                        :status, :created_at
                    )
                    RETURNING sequence_no
                    """
                ),
                {
                    "message_id": message.message_id,
                    "conversation_id": message.conversation_id,
                    "role": message.role,
                    "content": message.content,
                    "run_id": message.run_id,
                    "parent_message_id": message.parent_message_id,
                    "status": message.status,
                    "created_at": message.created_at,
                },
            )
            sequence_no = res.mappings().first()["sequence_no"]

            for att in attachments or []:
                await session.execute(
                    text(
                        """
                        INSERT INTO agent_conversation.message_attachments (
                            attachment_id, message_id, object_ref, media_type, file_name,
                            size, checksum, knowledge_ingest_status, created_at
                        ) VALUES (
                            :attachment_id, :message_id, :object_ref, :media_type, :file_name,
                            :size, :checksum, :knowledge_ingest_status, :created_at
                        )
                        """
                    ),
                    {
                        "attachment_id": att.attachment_id,
                        "message_id": message.message_id,
                        "object_ref": att.object_ref,
                        "media_type": att.media_type,
                        "file_name": att.file_name,
                        "size": att.size,
                        "checksum": att.checksum,
                        "knowledge_ingest_status": att.knowledge_ingest_status,
                        "created_at": att.created_at,
                    },
                )
            await session.commit()

        stored = message.model_copy(deep=True)
        stored.sequence_no = int(sequence_no)
        stored.attachments = list(attachments or [])
        return stored

    async def list_messages(self, conversation_id: str) -> list[MessageRecord]:
        async with self._session_factory() as session:
            msg_res = await session.execute(
                text(
                    """
                    SELECT message_id, conversation_id, sequence_no, role, content, run_id,
                           parent_message_id, status, created_at
                    FROM agent_conversation.messages
                    WHERE conversation_id = :conversation_id
                    ORDER BY sequence_no ASC
                    """
                ),
                {"conversation_id": conversation_id},
            )
            msg_rows = msg_res.mappings().all()
            if not msg_rows:
                return []

            att_res = await session.execute(
                text(
                    """
                    SELECT attachment_id, message_id, object_ref, media_type, file_name,
                           size, checksum, knowledge_ingest_status, created_at
                    FROM agent_conversation.message_attachments
                    WHERE message_id = ANY(:message_ids)
                    """
                ),
                {"message_ids": [r["message_id"] for r in msg_rows]},
            )
            attachments_by_message: dict[str, list[MessageAttachmentRecord]] = {}
            for r in att_res.mappings().all():
                attachments_by_message.setdefault(r["message_id"], []).append(
                    MessageAttachmentRecord(
                        attachment_id=r["attachment_id"],
                        message_id=r["message_id"],
                        object_ref=r["object_ref"],
                        media_type=r["media_type"],
                        file_name=r["file_name"],
                        size=r["size"],
                        checksum=r["checksum"],
                        knowledge_ingest_status=r["knowledge_ingest_status"],
                        created_at=r["created_at"],
                    )
                )

        return [
            MessageRecord(
                message_id=r["message_id"],
                conversation_id=r["conversation_id"],
                sequence_no=r["sequence_no"],
                role=r["role"],
                content=r["content"],
                run_id=r["run_id"],
                parent_message_id=r["parent_message_id"],
                status=r["status"],
                created_at=r["created_at"],
                attachments=attachments_by_message.get(r["message_id"], []),
            )
            for r in msg_rows
        ]

    @staticmethod
    def _parse_json(val: Any) -> Any:
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return val
        return val

    @classmethod
    def _row_to_conversation(cls, row: Any) -> ConversationRecord:
        return ConversationRecord(
            conversation_id=row["conversation_id"],
            workspace_id=row["workspace_id"],
            created_by_principal=row["created_by_principal"],
            title=row["title"],
            active_agent_profile=row["active_agent_profile"],
            metadata=cls._parse_json(row["metadata"]) or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            archived_at=row["archived_at"],
        )
