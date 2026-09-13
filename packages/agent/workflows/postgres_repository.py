from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent.workflows.repository import WorkflowDefinitionRecord, WorkflowDefinitionRepository
from agent.workflows.schema import WorkflowSpec

__all__ = ["PostgresWorkflowDefinitionRepository"]


class PostgresWorkflowDefinitionRepository(WorkflowDefinitionRepository):
    """PostgreSQL-backed durable repository for immutable Workflow definitions."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save_definition(
        self, spec: WorkflowSpec, workspace_id: str = "default"
    ) -> WorkflowDefinitionRecord:
        spec_data = spec.model_dump()
        def_hash = spec.definition_hash or spec.compute_hash()
        created_at = datetime.now(UTC)

        stmt = text(
            """
            INSERT INTO agent.workflow_definitions (
                workspace_id, workflow_asset_id, version, definition_hash, spec_data, description, created_at
            )
            VALUES (
                :ws_id, :wid, :version, :def_hash, CAST(:spec_data AS jsonb), :description, :created_at
            )
            ON CONFLICT (workspace_id, workflow_asset_id, version) DO UPDATE
            SET spec_data = EXCLUDED.spec_data,
                description = EXCLUDED.description
            WHERE agent.workflow_definitions.definition_hash = EXCLUDED.definition_hash
            RETURNING workspace_id, workflow_asset_id, version, definition_hash, spec_data, description, created_at
            """
        )

        async with self._session_factory() as session, session.begin():
            res = await session.execute(
                stmt,
                {
                    "ws_id": workspace_id,
                    "wid": spec.id,
                    "version": spec.version,
                    "def_hash": def_hash,
                    "spec_data": json.dumps(spec_data),
                    "description": spec.description or "",
                    "created_at": created_at,
                },
            )
            row = res.mappings().one_or_none()
            if not row:
                # Conflict on hash mismatch (attempted mutation of published version)
                existing = await self.get_definition(spec.id, spec.version, workspace_id)
                if existing and existing.definition_hash != def_hash:
                    raise ValueError(
                        f"Cannot mutate published workflow '{spec.id}' version '{spec.version}' "
                        f"(hash mismatch: {existing.definition_hash} != {def_hash})"
                    )
                if existing:
                    return existing
                raise RuntimeError(f"Failed to save workflow definition for {spec.id}")

            return WorkflowDefinitionRecord(
                workflow_id=row["workflow_asset_id"],
                version=row["version"],
                definition_hash=row["definition_hash"],
                spec_data=row["spec_data"] if isinstance(row["spec_data"], dict) else json.loads(row["spec_data"]),
                description=row["description"],
                created_at=row["created_at"],
                workspace_id=row["workspace_id"],
            )

    async def get_definition(
        self, workflow_id: str, version: str, workspace_id: str = "default"
    ) -> WorkflowDefinitionRecord | None:
        stmt = text(
            """
            SELECT workspace_id, workflow_asset_id, version, definition_hash, spec_data, description, created_at
            FROM agent.workflow_definitions
            WHERE workflow_asset_id = :wid AND version = :version AND workspace_id = :ws_id
            LIMIT 1
            """
        )
        async with self._session_factory() as session:
            res = await session.execute(stmt, {"wid": workflow_id, "version": version, "ws_id": workspace_id})
            row = res.mappings().one_or_none()
            if not row:
                return None

            return WorkflowDefinitionRecord(
                workflow_id=row["workflow_asset_id"],
                version=row["version"],
                definition_hash=row["definition_hash"],
                spec_data=row["spec_data"] if isinstance(row["spec_data"], dict) else json.loads(row["spec_data"]),
                description=row["description"],
                created_at=row["created_at"],
                workspace_id=row["workspace_id"],
            )

    async def get_by_hash(
        self, definition_hash: str, workspace_id: str | None = None
    ) -> WorkflowDefinitionRecord | None:
        if workspace_id is not None:
            stmt = text(
                """
                SELECT workspace_id, workflow_asset_id, version, definition_hash, spec_data, description, created_at
                FROM agent.workflow_definitions
                WHERE definition_hash = :def_hash AND workspace_id = :ws_id
                LIMIT 1
                """
            )
            params = {"def_hash": definition_hash, "ws_id": workspace_id}
        else:
            stmt = text(
                """
                SELECT workspace_id, workflow_asset_id, version, definition_hash, spec_data, description, created_at
                FROM agent.workflow_definitions
                WHERE definition_hash = :def_hash
                LIMIT 1
                """
            )
            params = {"def_hash": definition_hash}

        async with self._session_factory() as session:
            res = await session.execute(stmt, params)
            row = res.mappings().one_or_none()
            if not row:
                return None

            return WorkflowDefinitionRecord(
                workflow_id=row["workflow_asset_id"],
                version=row["version"],
                definition_hash=row["definition_hash"],
                spec_data=row["spec_data"] if isinstance(row["spec_data"], dict) else json.loads(row["spec_data"]),
                description=row["description"],
                created_at=row["created_at"],
                workspace_id=row["workspace_id"],
            )

    async def list_versions(
        self, workflow_id: str, workspace_id: str | None = None
    ) -> list[WorkflowDefinitionRecord]:
        if workspace_id:
            stmt = text(
                """
                SELECT workspace_id, workflow_asset_id, version, definition_hash, spec_data, description, created_at
                FROM agent.workflow_definitions
                WHERE workflow_asset_id = :wid AND workspace_id = :ws_id
                ORDER BY created_at ASC, version ASC
                """
            )
            params: dict[str, Any] = {"wid": workflow_id, "ws_id": workspace_id}
        else:
            stmt = text(
                """
                SELECT workspace_id, workflow_asset_id, version, definition_hash, spec_data, description, created_at
                FROM agent.workflow_definitions
                WHERE workflow_asset_id = :wid
                ORDER BY created_at ASC, version ASC
                """
            )
            params = {"wid": workflow_id}

        async with self._session_factory() as session:
            res = await session.execute(stmt, params)
            rows = res.mappings().all()
            return [
                WorkflowDefinitionRecord(
                    workflow_id=r["workflow_asset_id"],
                    version=r["version"],
                    definition_hash=r["definition_hash"],
                    spec_data=r["spec_data"] if isinstance(r["spec_data"], dict) else json.loads(r["spec_data"]),
                    description=r["description"],
                    created_at=r["created_at"],
                    workspace_id=r["workspace_id"],
                )
                for r in rows
            ]
