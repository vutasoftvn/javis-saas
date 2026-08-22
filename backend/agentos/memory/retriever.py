from __future__ import annotations

from agentos.core.models import TaskContext
from agentos.memory.models import MemoryItem
from agentos.memory.retrieval import MemoryQuery, score_relevance
from agentos.memory.store import MemoryStore

DEFAULT_MAX_SNIPPETS = 5
DEFAULT_MAX_CHARS_PER_SNIPPET = 280


class MemoryRetriever:
    """Retrieval pipeline: task -> query -> scope filter -> naive semantic
    scoring -> importance/recency ranking -> compression -> snippets.
    Policy filtering (blueprint §3.6/§13) is a pass-through hook here —
    Governance integration is a later phase.
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
        return relevance * 0.7 + item.importance * 0.3

    def _compress(self, content: str) -> str:
        if len(content) <= self._max_chars_per_snippet:
            return content
        return content[: self._max_chars_per_snippet - 1].rstrip() + "…"
