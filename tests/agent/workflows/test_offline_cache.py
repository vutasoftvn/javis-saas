from __future__ import annotations

import pytest

from agent.workflows.models import StepOutcome, StepStatus
from agent.workflows.offline_cache import CachingStep, InMemoryOfflineStepCacheStore, compute_cache_key


def test_compute_cache_key_is_deterministic():
    a = compute_cache_key("eval_suite", "hash_a", ("dep_hash_1", "dep_hash_2"))
    b = compute_cache_key("eval_suite", "hash_a", ("dep_hash_1", "dep_hash_2"))

    assert a == b


def test_compute_cache_key_ignores_dependency_order():
    a = compute_cache_key("eval_suite", "hash_a", ("dep_hash_1", "dep_hash_2"))
    b = compute_cache_key("eval_suite", "hash_a", ("dep_hash_2", "dep_hash_1"))

    assert a == b


def test_compute_cache_key_changes_when_semantic_fingerprint_changes():
    a = compute_cache_key("eval_suite", "hash_a", ())
    b = compute_cache_key("eval_suite", "hash_b", ())

    assert a != b


def test_compute_cache_key_changes_when_dependency_fingerprint_changes():
    a = compute_cache_key("eval_suite", "hash_a", ("dep_hash_1",))
    b = compute_cache_key("eval_suite", "hash_a", ("dep_hash_2",))

    assert a != b


def test_compute_cache_key_changes_when_step_kind_changes():
    a = compute_cache_key("eval_suite", "hash_a", ())
    b = compute_cache_key("knowledge_build", "hash_a", ())

    assert a != b


@pytest.mark.asyncio
async def test_in_memory_cache_store_returns_none_when_not_set():
    store = InMemoryOfflineStepCacheStore()

    result = await store.get("some_key")

    assert result is None


@pytest.mark.asyncio
async def test_in_memory_cache_store_roundtrip():
    store = InMemoryOfflineStepCacheStore()

    await store.set("some_key", {"output": "value"})
    result = await store.get("some_key")

    assert result == {"output": "value"}


class _CountingStep:
    """Step giả đếm số lần run() thật sự được gọi — dùng để verify cache
    hit không gọi lại step bên trong."""

    def __init__(self, name: str, updates: dict) -> None:
        self.name = name
        self.call_count = 0
        self._updates = updates

    async def run(self, state: dict) -> StepOutcome:
        self.call_count += 1
        return StepOutcome(status=StepStatus.COMPLETED, updates=self._updates)


class _FailingStep:
    name = "failing_step"

    async def run(self, state: dict) -> StepOutcome:
        return StepOutcome(status=StepStatus.FAILED, error="boom")


@pytest.mark.asyncio
async def test_caching_step_runs_inner_step_on_cache_miss():
    inner = _CountingStep("s1", {"x": 1})
    cache_store = InMemoryOfflineStepCacheStore()
    step = CachingStep(
        inner, step_kind="eval_suite", semantic_fingerprint="h1", cache_store=cache_store
    )

    outcome = await step.run({})

    assert outcome.status == StepStatus.COMPLETED
    assert outcome.updates == {"x": 1}
    assert inner.call_count == 1
    assert step.cache_hit is False


@pytest.mark.asyncio
async def test_caching_step_skips_inner_step_on_cache_hit():
    cache_store = InMemoryOfflineStepCacheStore()
    inner1 = _CountingStep("s1", {"x": 1})
    step1 = CachingStep(inner1, step_kind="eval_suite", semantic_fingerprint="h1", cache_store=cache_store)
    await step1.run({})

    inner2 = _CountingStep("s1", {"x": 999})  # nếu bị gọi thật, sẽ trả x=999 sai
    step2 = CachingStep(inner2, step_kind="eval_suite", semantic_fingerprint="h1", cache_store=cache_store)
    outcome = await step2.run({})

    assert outcome.status == StepStatus.COMPLETED
    assert outcome.updates == {"x": 1}  # kết quả từ cache, không phải inner2
    assert inner2.call_count == 0
    assert step2.cache_hit is True


@pytest.mark.asyncio
async def test_caching_step_invalidates_when_dependency_fingerprint_changes():
    cache_store = InMemoryOfflineStepCacheStore()
    inner1 = _CountingStep("s1", {"x": 1})
    step1 = CachingStep(
        inner1, step_kind="eval_suite", semantic_fingerprint="h1",
        dependency_fingerprints=("dep_v1",), cache_store=cache_store,
    )
    await step1.run({})

    inner2 = _CountingStep("s1", {"x": 2})
    step2 = CachingStep(
        inner2, step_kind="eval_suite", semantic_fingerprint="h1",
        dependency_fingerprints=("dep_v2",), cache_store=cache_store,  # dependency đổi
    )
    outcome = await step2.run({})

    assert outcome.updates == {"x": 2}  # chạy lại thật, không dùng cache cũ
    assert inner2.call_count == 1
    assert step2.cache_hit is False


@pytest.mark.asyncio
async def test_caching_step_does_not_cache_failed_outcome():
    cache_store = InMemoryOfflineStepCacheStore()
    step1 = CachingStep(_FailingStep(), step_kind="eval_suite", semantic_fingerprint="h1", cache_store=cache_store)
    outcome1 = await step1.run({})
    assert outcome1.status == StepStatus.FAILED

    inner2 = _CountingStep("s1", {"x": 1})
    step2 = CachingStep(inner2, step_kind="eval_suite", semantic_fingerprint="h1", cache_store=cache_store)
    outcome2 = await step2.run({})

    # FAILED không được cache — step2 phải chạy thật (cache miss), không kẹt ở lỗi cũ
    assert inner2.call_count == 1
    assert outcome2.status == StepStatus.COMPLETED


def test_caching_step_exposes_the_inner_step_name():
    inner = _CountingStep("my_step_name", {})
    step = CachingStep(
        inner, step_kind="eval_suite", semantic_fingerprint="h1", cache_store=InMemoryOfflineStepCacheStore()
    )

    assert step.name == "my_step_name"
