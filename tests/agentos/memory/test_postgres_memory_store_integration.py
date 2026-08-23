"""Integration test cho PostgresMemoryStore chạy với Postgres thật (không fake session).

Yêu cầu env var `AGENTOS_TEST_DATABASE_URL` trỏ tới 1 Postgres có schema `agent_memory`
(chạy migration `agentos/migrations/001_agent_memory_and_knowledge.sql` trước). Bỏ qua
(skip) nếu biến này không được set — CI không có Postgres vẫn chạy được suite còn lại.
"""
from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio

pytest.importorskip("asyncpg")

TEST_DATABASE_URL = os.environ.get("AGENTOS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENTOS_TEST_DATABASE_URL not set — skipping real-Postgres integration test",
)


@pytest_asyncio.fixture
async def session_factory():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_put_search_delete_roundtrip_against_real_postgres(session_factory):
    from agentos.memory.models import MemoryItem, MemoryKind
    from agentos.memory.providers.postgres import PostgresMemoryStore

    store = PostgresMemoryStore(db_session_factory=session_factory)
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    item = MemoryItem(
        workspace_id=workspace_id,
        agent_key="finance_agent",
        kind=MemoryKind.EPISODIC,
        content="Khách hàng chưa thanh toán hóa đơn tháng 8",
        importance=0.8,
        tags=["invoice"],
        metadata={"amount": 1000},
    )

    await store.put(item)

    results = await store.search(workspace_id=workspace_id, agent_key="finance_agent")
    assert len(results) == 1
    assert results[0].id == item.id
    assert results[0].content == item.content
    assert results[0].tags == ["invoice"]
    assert results[0].metadata == {"amount": 1000}

    await store.delete(item.id)
    results_after_delete = await store.search(workspace_id=workspace_id, agent_key="finance_agent")
    assert results_after_delete == []


@pytest.mark.asyncio
async def test_delete_missing_item_raises_not_found_against_real_postgres(session_factory):
    from agentos.memory.base import MemoryNotFoundError
    from agentos.memory.providers.postgres import PostgresMemoryStore

    store = PostgresMemoryStore(db_session_factory=session_factory)
    with pytest.raises(MemoryNotFoundError):
        await store.delete(f"missing-{uuid.uuid4().hex}")
