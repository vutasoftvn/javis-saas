from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable

from agent_core.artifacts.models import WorkspaceArtifact

__all__ = [
    "ArtifactRepository",
    "InMemoryArtifactRepository",
]


@runtime_checkable
class ArtifactRepository(Protocol):
    async def create(self, artifact: WorkspaceArtifact) -> WorkspaceArtifact: ...

    async def get(
        self, company_id: str, workspace_id: str, artifact_id: str
    ) -> Optional[WorkspaceArtifact]: ...

    async def list_for_conversation(
        self,
        company_id: str,
        workspace_id: str,
        conversation_id: str,
        include_archived: bool = False,
    ) -> list[WorkspaceArtifact]: ...

    async def archive(
        self, company_id: str, workspace_id: str, artifact_id: str
    ) -> Optional[WorkspaceArtifact]: ...


class InMemoryArtifactRepository:
    """In-memory implementation của ArtifactRepository cho test & dev."""

    def __init__(self) -> None:
        self._artifacts: dict[str, WorkspaceArtifact] = {}
        self._lock = asyncio.Lock()

    async def create(self, artifact: WorkspaceArtifact) -> WorkspaceArtifact:
        async with self._lock:
            stored = artifact.model_copy(deep=True)
            self._artifacts[stored.artifact_id] = stored
            return stored.model_copy(deep=True)

    async def get(
        self, company_id: str, workspace_id: str, artifact_id: str
    ) -> Optional[WorkspaceArtifact]:
        async with self._lock:
            art = self._artifacts.get(artifact_id)
            if art and art.company_id == company_id and art.workspace_id == workspace_id:
                return art.model_copy(deep=True)
            return None

    async def list_for_conversation(
        self,
        company_id: str,
        workspace_id: str,
        conversation_id: str,
        include_archived: bool = False,
    ) -> list[WorkspaceArtifact]:
        async with self._lock:
            results = [
                a.model_copy(deep=True)
                for a in self._artifacts.values()
                if a.company_id == company_id
                and a.workspace_id == workspace_id
                and a.conversation_id == conversation_id
                and (include_archived or a.status != "archived")
            ]
            results.sort(key=lambda x: x.created_at, reverse=True)
            return results

    async def archive(
        self, company_id: str, workspace_id: str, artifact_id: str
    ) -> Optional[WorkspaceArtifact]:
        async with self._lock:
            art = self._artifacts.get(artifact_id)
            if not art or art.company_id != company_id or art.workspace_id != workspace_id:
                return None
            art.status = "archived"
            art.archived_at = datetime.now(timezone.utc)
            return art.model_copy(deep=True)
