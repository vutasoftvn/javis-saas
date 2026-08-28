from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field

from agent_core.workflows.schema import WorkflowSpec

__all__ = [
    "InMemoryWorkflowDefinitionRepository",
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


class WorkflowDefinitionRepository(Protocol):
    """Hợp đồng lưu trữ lâu dài các WorkflowSpec đã được publish bất biến."""

    async def save_definition(self, spec: WorkflowSpec) -> WorkflowDefinitionRecord: ...

    async def get_definition(
        self, workflow_id: str, version: str
    ) -> WorkflowDefinitionRecord | None: ...

    async def get_by_hash(self, definition_hash: str) -> WorkflowDefinitionRecord | None: ...

    async def list_versions(self, workflow_id: str) -> list[WorkflowDefinitionRecord]: ...


class InMemoryWorkflowDefinitionRepository:
    """In-memory implementation của Durable Workflow Definition Repository."""

    def __init__(self) -> None:
        self._definitions: dict[
            tuple[str, str], WorkflowDefinitionRecord
        ] = {}  # (id, ver) -> record
        self._by_hash: dict[str, WorkflowDefinitionRecord] = {}

    async def save_definition(self, spec: WorkflowSpec) -> WorkflowDefinitionRecord:
        spec_dict = spec.model_dump()
        canonical_str = json.dumps(spec_dict, sort_keys=True, default=str)
        def_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        rec = WorkflowDefinitionRecord(
            workflow_id=spec.id,
            version=spec.version,
            definition_hash=def_hash,
            spec_data=spec_dict,
            description=spec.description,
            created_at=datetime.now(UTC),
        )
        self._definitions[(spec.id, spec.version)] = rec
        self._by_hash[def_hash] = rec
        return rec

    async def get_definition(
        self, workflow_id: str, version: str
    ) -> WorkflowDefinitionRecord | None:
        return self._definitions.get((workflow_id, version))

    async def get_by_hash(self, definition_hash: str) -> WorkflowDefinitionRecord | None:
        return self._by_hash.get(definition_hash)

    async def list_versions(self, workflow_id: str) -> list[WorkflowDefinitionRecord]:
        return [rec for (wid, _), rec in self._definitions.items() if wid == workflow_id]
