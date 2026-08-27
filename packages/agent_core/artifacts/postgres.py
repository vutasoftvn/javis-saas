from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import text

from agent_core.artifacts.models import WorkspaceArtifact

__all__ = ["PostgresArtifactRepository"]


class PostgresArtifactRepository:
    """PostgreSQL implementation cho WorkspaceArtifacts (agent_artifact.workspace_artifacts)."""

    def __init__(self, db_session_factory: Any) -> None:
        if db_session_factory is None:
            raise ValueError("PostgresArtifactRepository requires a valid db_session_factory.")
        self._session_factory = db_session_factory

    async def create(self, artifact: WorkspaceArtifact) -> WorkspaceArtifact:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_artifact.workspace_artifacts (
                        artifact_id, workspace_id, conversation_id, run_id,
                        source_message_id, artifact_kind, display_name, media_type,
                        object_ref, checksum, size_bytes, status, input_artifact_ids,
                        created_at, archived_at
                    ) VALUES (
                        :artifact_id, :workspace_id, :conversation_id, :run_id,
                        :source_message_id, :artifact_kind, :display_name, :media_type,
                        :object_ref, :checksum, :size_bytes, :status, :input_artifact_ids,
                        :created_at, :archived_at
                    )
                    """
                ),
                {
                    "artifact_id": artifact.artifact_id,
                    "workspace_id": artifact.workspace_id,
                    "conversation_id": artifact.conversation_id,
                    "run_id": artifact.run_id,
                    "source_message_id": artifact.source_message_id,
                    "artifact_kind": artifact.artifact_kind,
                    "display_name": artifact.display_name,
                    "media_type": artifact.media_type,
                    "object_ref": artifact.object_ref,
                    "checksum": artifact.checksum,
                    "size_bytes": artifact.size_bytes,
                    "status": artifact.status,
                    "input_artifact_ids": json.dumps(artifact.input_artifact_ids),
                    "created_at": artifact.created_at,
                    "archived_at": artifact.archived_at,
                },
            )
            await session.commit()
        return artifact

    async def get(
        self, workspace_id: str, artifact_id: str
    ) -> Optional[WorkspaceArtifact]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT artifact_id, workspace_id, conversation_id, run_id,
                           source_message_id, artifact_kind, display_name, media_type,
                           object_ref, checksum, size_bytes, status, input_artifact_ids,
                           created_at, archived_at
                    FROM agent_artifact.workspace_artifacts
                    WHERE artifact_id = :artifact_id
                      AND workspace_id = :workspace_id
                    """
                ),
                {
                    "artifact_id": artifact_id,
                    "workspace_id": workspace_id,
                },
            )
            row = res.mappings().first()
            return self._row_to_artifact(row) if row else None

    async def list_for_conversation(
        self,
        workspace_id: str,
        conversation_id: str,
        include_archived: bool = False,
    ) -> list[WorkspaceArtifact]:
        query = """
            SELECT artifact_id, workspace_id, conversation_id, run_id,
                   source_message_id, artifact_kind, display_name, media_type,
                   object_ref, checksum, size_bytes, status, input_artifact_ids,
                   created_at, archived_at
            FROM agent_artifact.workspace_artifacts
            WHERE workspace_id = :workspace_id
              AND conversation_id = :conversation_id
        """
        if not include_archived:
            query += " AND status != 'archived'"
        query += " ORDER BY created_at DESC"

        async with self._session_factory() as session:
            res = await session.execute(
                text(query),
                {
                    "workspace_id": workspace_id,
                    "conversation_id": conversation_id,
                },
            )
            rows = res.mappings().all()
            return [self._row_to_artifact(r) for r in rows]

    async def archive(
        self, workspace_id: str, artifact_id: str
    ) -> Optional[WorkspaceArtifact]:
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    UPDATE agent_artifact.workspace_artifacts
                    SET status = 'archived',
                        archived_at = :archived_at
                    WHERE artifact_id = :artifact_id
                      AND workspace_id = :workspace_id
                    """
                ),
                {
                    "artifact_id": artifact_id,
                    "workspace_id": workspace_id,
                    "archived_at": now,
                },
            )
            await session.commit()
            if res.rowcount == 0:
                return None
        return await self.get(workspace_id, artifact_id)

    @classmethod
    def _row_to_artifact(cls, row: Any) -> WorkspaceArtifact:
        input_ids = row["input_artifact_ids"]
        if isinstance(input_ids, str):
            try:
                input_ids = json.loads(input_ids)
            except Exception:
                input_ids = []
        elif not isinstance(input_ids, list):
            input_ids = []

        return WorkspaceArtifact(
            artifact_id=row["artifact_id"],
            workspace_id=row["workspace_id"],
            conversation_id=row["conversation_id"],
            run_id=row["run_id"],
            source_message_id=row["source_message_id"],
            artifact_kind=row["artifact_kind"],
            display_name=row["display_name"],
            media_type=row["media_type"],
            object_ref=row["object_ref"],
            checksum=row["checksum"],
            size_bytes=int(row["size_bytes"]),
            status=row["status"],
            input_artifact_ids=input_ids,
            created_at=row["created_at"],
            archived_at=row["archived_at"],
        )
