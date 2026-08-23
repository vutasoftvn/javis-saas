"""Integration test cho PostgresMemoryStore chạy với Postgres thật —
port từ legacy/agent_runtime_archive/agentos/memory/providers/postgres.py,
điều chỉnh theo MemoryItem model canonical (packages/agent_core/memory/models.py)."""
from __future__ import annotations

import os

import pytest
import pytest_asyncio

pytest.importorskip("asyncpg")

TEST_DATABASE_URL = os.environ.get("AGENT_CORE_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENT_CORE_TEST_DATABASE_URL not set",
)


@pytest_asyncio.fixture
async def session_factory():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def test_postgres_memory_store_requires_session_factory():
    from agent_core.memory.base import ConfigurationError
    from agent_core.memory.providers.postgres import PostgresMemoryStore

    with pytest.raises(ConfigurationError):
        PostgresMemoryStore(db_session_factory=None)


@pytest.mark.asyncio
async def test_put_and_search_roundtrip_scoped_by_workspace(session_factory):
    from agent_core.memory.models import MemoryItem, MemoryKind
    from agent_core.memory.providers.postgres import PostgresMemoryStore

    store = PostgresMemoryStore(db_session_factory=session_factory)
    workspace_id = "ws-memory-test"

    item = MemoryItem(
        workspace_id=workspace_id,
        agent_key="finance-cfo",
        kind=MemoryKind.EPISODIC,
        content="Q3 budget approved at 500M VND",
        tenant_id="tenant-1",
        provenance_run_id="run-abc",
    )
    await store.put(item)

    results = await store.search(workspace_id=workspace_id, agent_key="finance-cfo")

    assert len(results) == 1
    assert results[0].id == item.id
    assert results[0].content == item.content
    assert results[0].kind == MemoryKind.EPISODIC
    # tenant_id/provenance_run_id không có cột riêng trong migration hiện tại —
    # phải roundtrip đúng qua metadata JSONB, không được mất dữ liệu.
    assert results[0].tenant_id == "tenant-1"
    assert results[0].provenance_run_id == "run-abc"


@pytest.mark.asyncio
async def test_search_does_not_leak_across_workspaces(session_factory):
    from agent_core.memory.models import MemoryItem, MemoryKind
    from agent_core.memory.providers.postgres import PostgresMemoryStore

    store = PostgresMemoryStore(db_session_factory=session_factory)

    await store.put(MemoryItem(workspace_id="ws-a", agent_key="x", kind=MemoryKind.WORKING, content="secret A"))
    await store.put(MemoryItem(workspace_id="ws-b", agent_key="x", kind=MemoryKind.WORKING, content="secret B"))

    results_a = await store.search(workspace_id="ws-a")

    assert len(results_a) == 1
    assert results_a[0].content == "secret A"


@pytest.mark.asyncio
async def test_delete_removes_item(session_factory):
    from agent_core.memory.models import MemoryItem, MemoryKind
    from agent_core.memory.providers.postgres import PostgresMemoryStore

    store = PostgresMemoryStore(db_session_factory=session_factory)
    item = MemoryItem(workspace_id="ws-delete-test", agent_key="x", kind=MemoryKind.WORKING, content="to delete")
    await store.put(item)

    await store.delete(item.id)

    results = await store.search(workspace_id="ws-delete-test")
    assert results == []


@pytest.mark.asyncio
async def test_delete_unknown_item_raises_not_found(session_factory):
    from agent_core.memory.base import MemoryNotFoundError
    from agent_core.memory.providers.postgres import PostgresMemoryStore

    store = PostgresMemoryStore(db_session_factory=session_factory)

    with pytest.raises(MemoryNotFoundError):
        await store.delete("unknown-id")
