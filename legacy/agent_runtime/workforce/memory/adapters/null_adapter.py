from typing import Any, Optional

from workforce.memory.gateway import AgentMemoryGateway


class NullAgentMemoryAdapter(AgentMemoryGateway):
    """Default adapter (ADR-MEM-001, ADR-MEM-002) - used whenever
    `FLAG_AGENT_MEMORY_V12_3` is off or the configured engine is
    unreachable. Always returns empty/unavailable results rather than
    raising, so callers degrade gracefully (spec §181): mCOSA "must
    continue operating without Agent Memory"."""

    async def capture(self, event: dict) -> None:
        return None

    async def recall(self, query: dict) -> list[dict]:
        return []

    async def search(self, query: dict) -> list[dict]:
        return []

    async def get_task_context(self, task_id: str) -> Optional[dict]:
        return None

    async def get_scenario(self, scenario_id: str) -> Optional[dict]:
        return None

    async def get_profile(self, subject_id: str) -> Optional[dict]:
        return None

    async def end_session(self, session_id: str) -> None:
        return None

    async def promote_candidate(self, candidate_id: str) -> dict:
        return {"status": "unavailable"}

    async def forget(self, memory_id: str) -> None:
        return None

    async def export(self, scope: dict) -> Any:
        return []
