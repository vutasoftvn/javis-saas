"""P1 Task 6: production MemoryService không được âm thầm dựng InMemoryMemoryStore.
`store` là tham số bắt buộc; muốn in-memory phải nói rõ."""
import pytest

from agent.memory.retention import RetentionPolicy
from agent.memory.service import MemoryService
from agent.memory.store import InMemoryMemoryStore


def test_init_requires_explicit_store():
    with pytest.raises(TypeError):
        MemoryService()  # type: ignore[call-arg]


def test_in_memory_helper_is_explicit():
    svc = MemoryService.in_memory()
    assert isinstance(svc._store, InMemoryMemoryStore)
    assert svc._retention is not None


def test_for_production_fails_without_database_url(monkeypatch):
    monkeypatch.delenv("AGENT_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="AGENT_DATABASE_URL"):
        MemoryService.for_production()


def test_explicit_store_still_works_positionally():
    svc = MemoryService(InMemoryMemoryStore())
    assert svc._retention is not None  # default RetentionPolicy


def test_explicit_retention_is_carried():
    policy = RetentionPolicy(max_items_per_scope=42)
    svc = MemoryService(InMemoryMemoryStore(), retention=policy)
    assert svc._retention.max_items_per_scope == 42
