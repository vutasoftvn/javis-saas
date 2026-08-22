from __future__ import annotations

from agentos.core.model_provider import ModelProvider
from agentos.core.models import TaskContext
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.store import MemoryStore

CONSOLIDATION_SYSTEM_PROMPT = (
    "Summarize the following agent run into one or two sentences of durable "
    "episodic memory. Be factual, do not invent details."
)


class EpisodeConsolidator:
    """Raw run trace -> summary -> episodic MemoryItem (blueprint §3.6
    consolidation lifecycle, first stage only: raw events -> episode ->
    summary). Fact extraction into SEMANTIC memory is a later phase.
    """

    def __init__(self, model_provider: ModelProvider, store: MemoryStore) -> None:
        self._model_provider = model_provider
        self._store = store

    async def consolidate(self, task: TaskContext, raw_episode_text: str) -> MemoryItem:
        response = await self._model_provider.generate(
            system_prompt=CONSOLIDATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": raw_episode_text}],
        )
        summary = response.text or raw_episode_text
        item = MemoryItem(
            workspace_id=task.workspace_id,
            agent_key=task.agent_key,
            kind=MemoryKind.EPISODIC,
            content=summary,
            tags=["consolidated"],
        )
        await self._store.put(item)
        return item
