from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field

from agent.workflows.schema import WorkflowSpec

__all__ = [
    "InMemoryWorkflowDefinitionRepository",
    "PostgresWorkflowDefinitionRepository",
    "WorkflowDefinitionRecord",
    "WorkflowDefinitionRepository",
]


class WorkflowDefinitionRecord(BaseModel):
    """Bản ghi định nghĩa Workflow bất biến được lưu trữ lâu dài theo Master Guide §10.3."""

    workflow_id: str
    version: str
    definition_hash: str
    spec_data: dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    description: str | None = None
    workspace_id: str = "default"


class WorkflowDefinitionRepository(Protocol):
    """Hợp đồng lưu trữ lâu dài các WorkflowSpec đã được publish bất biến."""

    async def save_definition(
        self, spec: WorkflowSpec, workspace_id: str = "default"
    ) -> WorkflowDefinitionRecord: ...

    async def get_definition(
        self, workflow_id: str, version: str, workspace_id: str = "default"
    ) -> WorkflowDefinitionRecord | None: ...

    async def get_by_hash(
        self, definition_hash: str, workspace_id: str | None = None
    ) -> WorkflowDefinitionRecord | None: ...

    async def list_versions(
        self, workflow_id: str, workspace_id: str | None = None
    ) -> list[WorkflowDefinitionRecord]: ...


class InMemoryWorkflowDefinitionRepository:
    """In-memory implementation của Durable Workflow Definition Repository."""

    def __init__(self) -> None:
        self._definitions: dict[
            tuple[str, str, str], WorkflowDefinitionRecord
        ] = {}  # (ws_id, id, ver) -> record
        self._by_hash: dict[str, WorkflowDefinitionRecord] = {}

    async def save_definition(
        self, spec: WorkflowSpec, workspace_id: str = "default"
    ) -> WorkflowDefinitionRecord:
        spec_dict = spec.model_dump()
        def_hash = spec.definition_hash or spec.compute_hash()

        rec = WorkflowDefinitionRecord(
            workflow_id=spec.id,
            version=spec.version,
            definition_hash=def_hash,
            spec_data=spec_dict,
            description=spec.description,
            created_at=datetime.now(UTC),
            workspace_id=workspace_id,
        )
        self._definitions[(workspace_id, spec.id, spec.version)] = rec
        self._by_hash[def_hash] = rec
        return rec

    async def get_definition(
        self, workflow_id: str, version: str, workspace_id: str = "default"
    ) -> WorkflowDefinitionRecord | None:
        return self._definitions.get((workspace_id, workflow_id, version))

    async def get_by_hash(
        self, definition_hash: str, workspace_id: str | None = None
    ) -> WorkflowDefinitionRecord | None:
        if workspace_id is not None:
            return next(
                (
                    r
                    for (ws, _, _), r in self._definitions.items()
                    if ws == workspace_id and r.definition_hash == definition_hash
                ),
                None,
            )
        return self._by_hash.get(definition_hash)

    async def list_versions(
        self, workflow_id: str, workspace_id: str | None = None
    ) -> list[WorkflowDefinitionRecord]:
        if workspace_id:
            return [
                rec
                for (ws, wid, _), rec in self._definitions.items()
                if wid == workflow_id and ws == workspace_id
            ]
        return [rec for (_, wid, _), rec in self._definitions.items() if wid == workflow_id]


def __getattr__(name: str) -> Any:
    if name == "PostgresWorkflowDefinitionRepository":
        from agent.workflows.postgres_repository import PostgresWorkflowDefinitionRepository
        return PostgresWorkflowDefinitionRepository
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


