from __future__ import annotations

from agentos.core.model_provider import ModelProvider
from agentos.core.models import TaskContext
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.store import MemoryStore

CONSOLIDATION_SYSTEM_PROMPT = (
    "Summarize the following agent run into one or two sentences of durable "
    "episodic memory. Be factual, do not invent details."
)

PROCEDURAL_CONSOLIDATION_SYSTEM_PROMPT = (
    "The following are several episodic memories describing the same "
    "repeated task. Write one or two sentences describing the general "
    "PROCEDURE (the reusable steps/approach), not any single instance's "
    "specific details. Be factual, do not invent steps that don't appear "
    "in the input."
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


DEFAULT_PROCEDURAL_MIN_OCCURRENCES = 3


class ProceduralConsolidator:
    """episodic (lặp lại) -> procedural (blueprint §3.6, giai đoạn 2 của
    consolidation lifecycle: raw events -> episode -> summary -> [đây] fact
    extraction -> semantic/procedural). Không có hạ tầng embedding/vector
    DB trong repo (xác nhận ở docs/architecture/AI_AGENT_OS_AUDIT_NOTES.md
    §0.3 — Knowledge Layer chưa implement), nên việc "phát hiện pattern lặp
    lại" ở đây KHÔNG dùng semantic clustering mà dùng `pattern_tag` do
    caller tự gán tường minh khi ghi episodic memory (ví dụ: chữ ký chuỗi
    tool-call) — trung thực về giới hạn, không giả vờ có clustering thật.
    """

    def __init__(self, model_provider: ModelProvider, store: MemoryStore) -> None:
        self._model_provider = model_provider
        self._store = store

    async def maybe_consolidate(
        self,
        *,
        workspace_id: str,
        agent_key: str,
        pattern_tag: str,
        min_occurrences: int = DEFAULT_PROCEDURAL_MIN_OCCURRENCES,
    ) -> MemoryItem | None:
        """Nếu đã có >= `min_occurrences` episodic memory mang `pattern_tag`
        và chưa có procedural memory nào cho pattern này, tóm tắt chúng
        thành 1 MemoryItem kind=PROCEDURAL. Trả None nếu chưa đủ ngưỡng hoặc
        procedural đã tồn tại — không tạo trùng lặp mỗi lần gọi lại.
        """
        procedural_existing = await self._store.search(
            workspace_id=workspace_id, agent_key=agent_key, kind=MemoryKind.PROCEDURAL, limit=100
        )
        if any(pattern_tag in item.tags for item in procedural_existing):
            return None

        episodes = await self._store.search(
            workspace_id=workspace_id, agent_key=agent_key, kind=MemoryKind.EPISODIC, limit=100
        )
        matching = [item for item in episodes if pattern_tag in item.tags]
        if len(matching) < min_occurrences:
            return None

        combined_text = "\n".join(f"- {item.content}" for item in matching)
        response = await self._model_provider.generate(
            system_prompt=PROCEDURAL_CONSOLIDATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": combined_text}],
        )
        summary = response.text or combined_text

        item = MemoryItem(
            workspace_id=workspace_id,
            agent_key=agent_key,
            kind=MemoryKind.PROCEDURAL,
            content=summary,
            tags=[pattern_tag, "procedural"],
            metadata={"derived_from_episode_count": len(matching)},
        )
        await self._store.put(item)
        return item
