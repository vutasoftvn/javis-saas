from __future__ import annotations

from datetime import datetime, timezone

from agentos.core.models import TaskContext
from agentos.memory.models import MemoryItem
from agentos.memory.retrieval import MemoryQuery, score_relevance
from agentos.memory.store import MemoryStore

DEFAULT_MAX_SNIPPETS = 5
DEFAULT_MAX_CHARS_PER_SNIPPET = 280


def compute_recency_factor(created_at: datetime) -> float:
    """Compute recency factor in (0, 1] using time decay with a 3-day half-life."""
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    delta_seconds = max(0.0, (now - created_at).total_seconds())
    return 1.0 / (1.0 + delta_seconds / 259200.0)


class MemoryRetriever:
    """Retrieval pipeline: task -> query -> scope filter -> Unicode relevance
    scoring -> importance/recency ranking (0.6*relevance + 0.25*importance + 0.15*recency)
    -> compression -> snippets.
    
    Policy filtering (blueprint §3.6/§13) is a pass-through hook here.
    """

    def __init__(
        self,
        store: MemoryStore,
        max_snippets: int = DEFAULT_MAX_SNIPPETS,
        max_chars_per_snippet: int = DEFAULT_MAX_CHARS_PER_SNIPPET,
    ) -> None:
        self._store = store
        self._max_snippets = max_snippets
        self._max_chars_per_snippet = max_chars_per_snippet

    async def retrieve(self, task: TaskContext) -> list[str]:
        query = MemoryQuery(workspace_id=task.workspace_id, agent_key=task.agent_key, text=task.goal)
        candidates = await self._store.search(
            workspace_id=query.workspace_id,
            agent_key=query.agent_key,
            limit=max(query.limit, self._max_snippets * 4),
        )
        ranked = sorted(candidates, key=lambda item: self._rank_key(query, item), reverse=True)
        relevant = [item for item in ranked if score_relevance(query.text, item.content) > 0]
        top = relevant[: self._max_snippets]
        return [self._compress(item.content) for item in top]

    def _rank_key(self, query: MemoryQuery, item: MemoryItem) -> float:
        relevance = score_relevance(query.text, item.content)
        recency = compute_recency_factor(item.created_at)
        return relevance * 0.6 + item.importance * 0.25 + recency * 0.15

    def _compress(self, content: str) -> str:
        if len(content) <= self._max_chars_per_snippet:
            return content
        return content[: self._max_chars_per_snippet - 1].rstrip() + "…"
