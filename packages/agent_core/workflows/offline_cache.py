from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from agent_core.governance.hashing import definition_hash

__all__ = ["compute_cache_key", "OfflineStepCacheStore", "InMemoryOfflineStepCacheStore"]


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

    async def get(self, cache_key: str) -> Optional[dict[str, Any]]: ...
    async def set(self, cache_key: str, outcome_updates: dict[str, Any]) -> None: ...


class InMemoryOfflineStepCacheStore:
    """Cache backend in-memory — đủ dùng cho pipeline chạy trong 1 process
    (vd 1 lần chạy Skill Optimization Lab hoặc 1 lần build offline). Không
    durable qua restart — xem docstring OfflineStepCacheStore."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def get(self, cache_key: str) -> Optional[dict[str, Any]]:
        cached = self._store.get(cache_key)
        return dict(cached) if cached is not None else None

    async def set(self, cache_key: str, outcome_updates: dict[str, Any]) -> None:
        self._store[cache_key] = dict(outcome_updates)
