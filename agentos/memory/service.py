from __future__ import annotations

from typing import Any, Optional

from agentos.core.model_provider import ModelProvider
from agentos.core.models import TaskContext
from agentos.memory.consolidation import EpisodeConsolidator, ProceduralConsolidator
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.retrieval import score_relevance
from agentos.memory.store import MemoryStore


class MemoryService:
    """Higher-level semantic memory service built on top of `MemoryStore`.
    
    Provides unified lifecycle methods: remember, recall, forget, and consolidation
    (episodic summarization & procedural pattern extraction).
    """

    def __init__(
        self,
        store: MemoryStore,
        model_provider: Optional[ModelProvider] = None,
    ) -> None:
        self._store = store
        self._model_provider = model_provider
        self._episode_consolidator = (
            EpisodeConsolidator(model_provider, store) if model_provider else None
        )
        self._procedural_consolidator = (
            ProceduralConsolidator(model_provider, store) if model_provider else None
        )

    async def remember(
        self,
        item_or_content: MemoryItem | str,
        *,
        workspace_id: Optional[str] = None,
        agent_key: Optional[str] = None,
        kind: MemoryKind = MemoryKind.EPISODIC,
        importance: float = 0.5,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> MemoryItem:
        """Store a new memory item."""
        if isinstance(item_or_content, MemoryItem):
            item = item_or_content
        else:
            if workspace_id is None or agent_key is None:
                raise ValueError("workspace_id and agent_key are required when storing raw content string")
            item = MemoryItem(
                workspace_id=workspace_id,
                agent_key=agent_key,
                kind=kind,
                content=item_or_content,
                importance=importance,
                tags=tags or [],
                metadata=metadata or {},
            )
        await self._store.put(item)
        return item

    async def recall(
        self,
        *,
        workspace_id: str,
        agent_key: Optional[str] = None,
        kind: Optional[MemoryKind] = None,
        query_text: Optional[str] = None,
        limit: int = 20,
    ) -> list[MemoryItem]:
        """Query and optionally rank relevant memories for a workspace and agent."""
        candidates = await self._store.search(
            workspace_id=workspace_id,
            agent_key=agent_key,
            kind=kind,
            limit=max(limit * 3, 20) if query_text else limit,
        )
        if not query_text:
            return candidates[:limit]

        # Rank candidates by relevance score
        scored = [
            (item, score_relevance(query_text, item.content))
            for item in candidates
        ]
        relevant = [
            item
            for item, score in sorted(scored, key=lambda pair: (pair[1], pair[0].importance), reverse=True)
            if score > 0
        ]
        return (relevant if relevant else candidates)[:limit]

    async def forget(self, item_id: str) -> None:
        """Delete a memory item by ID."""
        await self._store.delete(item_id)

    async def consolidate_episode(self, task: TaskContext, raw_episode_text: str) -> MemoryItem:
        """Summarize runtime execution traces into durable episodic memory."""
        if self._episode_consolidator is None:
            raise RuntimeError("ModelProvider is required for episode consolidation")
        return await self._episode_consolidator.consolidate(task, raw_episode_text)

    async def consolidate_procedural(
        self,
        *,
        workspace_id: str,
        agent_key: str,
        pattern_tag: str,
        min_occurrences: int = 3,
    ) -> Optional[MemoryItem]:
        """Extract recurring episodic patterns into reusable procedural memory."""
        if self._procedural_consolidator is None:
            raise RuntimeError("ModelProvider is required for procedural consolidation")
        return await self._procedural_consolidator.maybe_consolidate(
            workspace_id=workspace_id,
            agent_key=agent_key,
            pattern_tag=pattern_tag,
            min_occurrences=min_occurrences,
        )
