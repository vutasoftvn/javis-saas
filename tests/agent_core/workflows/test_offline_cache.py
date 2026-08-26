from __future__ import annotations

import pytest

from agent_core.workflows.offline_cache import InMemoryOfflineStepCacheStore, compute_cache_key


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
