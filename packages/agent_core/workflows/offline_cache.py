from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from agent_core.governance.hashing import definition_hash
from agent_core.workflows.models import StepOutcome, StepStatus
from agent_core.workflows.steps import WorkflowStep

__all__ = [
    "CachingStep",
    "InMemoryOfflineStepCacheStore",
    "OfflineStepCacheStore",
    "compute_cache_key",
]


def compute_cache_key(
    step_kind: str,
    semantic_fingerprint: str,
    dependency_fingerprints: tuple[str, ...] = (),
) -> str:
    """Cache key cho 1 offline step — CHỈ gồm step_kind + semantic
    fingerprint + dependency fingerprint (đã sort, không phân biệt thứ tự).
    KHÔNG bao gồm giá trị execution-only (worker/region/hostname/retry) —
    Wave M5, theo §23.3 của COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_
    PLAN_2026-08-26.md."""
    data = {
        "step_kind": step_kind,
        "semantic_fingerprint": semantic_fingerprint,
        "dependency_fingerprints": sorted(dependency_fingerprints),
    }
    return definition_hash(data)


@runtime_checkable
class OfflineStepCacheStore(Protocol):
    """Protocol cho cache backend của offline step — KHÔNG phải nguồn sự
    thật, chỉ để skip lại công việc đã làm. Mất cache (vd process restart)
    không mất dữ liệu thật, chỉ làm pipeline chạy lại từ đầu."""

    async def get(self, cache_key: str) -> dict[str, Any] | None: ...
    async def set(self, cache_key: str, outcome_updates: dict[str, Any]) -> None: ...


class InMemoryOfflineStepCacheStore:
    """Cache backend in-memory — đủ dùng cho pipeline chạy trong 1 process
    (vd 1 lần chạy Skill Optimization Lab hoặc 1 lần build offline). Không
    durable qua restart — xem docstring OfflineStepCacheStore."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def get(self, cache_key: str) -> dict[str, Any] | None:
        cached = self._store.get(cache_key)
        return dict(cached) if cached is not None else None

    async def set(self, cache_key: str, outcome_updates: dict[str, Any]) -> None:
        self._store[cache_key] = dict(outcome_updates)


class CachingStep:
    """Bọc 1 WorkflowStep với cache theo artifact fingerprint — CHỈ dùng cho
    offline eval/build pipeline (Wave M5), KHÔNG dùng cho online agent Run
    (INV-A5). Cache hit khi (step_kind, semantic_fingerprint,
    dependency_fingerprints) không đổi VÀ lần chạy trước status=COMPLETED —
    FAILED không bao giờ được cache (không kẹt pipeline ở lỗi cũ nếu retry)."""

    def __init__(
        self,
        step: WorkflowStep,
        *,
        step_kind: str,
        semantic_fingerprint: str,
        dependency_fingerprints: tuple[str, ...] = (),
        cache_store: OfflineStepCacheStore,
    ) -> None:
        self.name = step.name
        self._step = step
        self._cache_key = compute_cache_key(
            step_kind, semantic_fingerprint, dependency_fingerprints
        )
        self._cache_store = cache_store
        self.cache_hit = False

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        cached = await self._cache_store.get(self._cache_key)
        if cached is not None:
            self.cache_hit = True
            return StepOutcome(status=StepStatus.COMPLETED, updates=cached)

        outcome = await self._step.run(state)
        if outcome.status == StepStatus.COMPLETED:
            await self._cache_store.set(self._cache_key, outcome.updates)
        return outcome
