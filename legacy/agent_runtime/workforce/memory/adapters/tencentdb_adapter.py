import logging
from typing import Any, Optional

import httpx

from workforce.memory.gateway import AgentMemoryGateway

logger = logging.getLogger("mcosa.agent_memory.tencentdb_adapter")


class TencentDBAgentMemoryAdapter(AgentMemoryGateway):
    """First concrete AgentMemoryGateway adapter (ADR-MEM-001), talking to a
    local TencentDB-Agent-Memory sidecar over loopback only (ADR-MEM-002,
    spec §146/§178).

    IMPORTANT: the HTTP paths/payload shapes below are this adapter's own
    facade contract, not yet verified against a pinned
    TencentCloud/TencentDB-Agent-Memory release. Spec §216 requires pinning
    a specific compatible release during PoC rather than tracking the
    repository's latest branch - confirm/adjust these paths against that
    release's actual API during the MEM-1 Claude Code PoC before enabling
    this adapter anywhere real. Until then, `NullAgentMemoryAdapter` is the
    safe default (see `service.py::get_gateway`).

    Every method catches connection/timeout errors and degrades to the same
    empty/unavailable shape `NullAgentMemoryAdapter` returns, rather than
    raising - a down sidecar must never break the caller (spec §181).
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8765", timeout_seconds: float = 5.0):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    async def _post(self, path: str, payload: dict) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
                response = await client.post(path, json=payload)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.warning("TencentDBAgentMemoryAdapter %s failed: %s", path, exc)
            return None

    async def capture(self, event: dict) -> None:
        await self._post("/v1/memory/capture", event)

    async def recall(self, query: dict) -> list[dict]:
        result = await self._post("/v1/memory/recall", query)
        return (result or {}).get("memories", [])

    async def search(self, query: dict) -> list[dict]:
        result = await self._post("/v1/memory/search", query)
        return (result or {}).get("memories", [])

    async def get_task_context(self, task_id: str) -> Optional[dict]:
        result = await self._post("/v1/memory/task_context", {"task_id": task_id})
        return (result or {}).get("context")

    async def get_scenario(self, scenario_id: str) -> Optional[dict]:
        result = await self._post("/v1/memory/scenario", {"scenario_id": scenario_id})
        return (result or {}).get("scenario")

    async def get_profile(self, subject_id: str) -> Optional[dict]:
        result = await self._post("/v1/memory/profile", {"subject_id": subject_id})
        return (result or {}).get("profile")

    async def end_session(self, session_id: str) -> None:
        await self._post("/v1/memory/end_session", {"session_id": session_id})

    async def promote_candidate(self, candidate_id: str) -> dict:
        result = await self._post("/v1/memory/promote", {"candidate_id": candidate_id})
        return result or {"status": "unavailable"}

    async def forget(self, memory_id: str) -> None:
        await self._post("/v1/memory/forget", {"memory_id": memory_id})

    async def export(self, scope: dict) -> Any:
        result = await self._post("/v1/memory/export", scope)
        return (result or {}).get("items", [])
