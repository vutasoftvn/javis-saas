from __future__ import annotations

import datetime
import json
import pytest

from agentos.memory.exceptions import ConfigurationError, MemoryNotFoundError
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.providers.postgres import PostgresMemoryStore


class _FakeResult:
    def __init__(self, rows: list[tuple] | None = None) -> None:
        self._rows = rows or []

    def fetchall(self) -> list[tuple]:
        return self._rows

    def fetchone(self) -> tuple | None:
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(self, fetch_result: _FakeResult | None = None) -> None:
        self.executed: list[tuple[str, dict]] = []
        self.committed = False
        self._fetch_result = fetch_result or _FakeResult()

    async def execute(self, sql: str, params: dict | None = None):
        self.executed.append((str(sql), params or {}))
        return self._fetch_result

    async def commit(self) -> None:
        self.committed = True

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *exc) -> None:
        return None


def _session_factory(session: _FakeSession):
    return lambda: session


def test_init_without_session_factory_raises_configuration_error():
    with pytest.raises(ConfigurationError) as exc_info:
        PostgresMemoryStore(db_session_factory=None)
    assert "requires a valid `db_session_factory`" in str(exc_info.value)


@pytest.mark.asyncio
async def test_put_memory_item_inserts_into_agent_memory_schema():
    session = _FakeSession()
    store = PostgresMemoryStore(db_session_factory=_session_factory(session))
    item = MemoryItem(
        workspace_id="ws1",
        agent_key="finance_agent",
        kind=MemoryKind.EPISODIC,
        content="Invoice 123 reconciled",
        importance=0.8,
        tags=["invoice", "reconciliation"],
        metadata={"amount": 1000},
    )

    await store.put(item)

    assert session.committed is True
    sql, params = session.executed[0]
    assert "INSERT INTO agent_memory.agent_memories" in sql
    assert params["id"] == item.id
    assert params["workspace_id"] == "ws1"
    assert params["agent_key"] == "finance_agent"
    assert params["kind"] == "EPISODIC"
    assert params["importance"] == 0.8
    assert json.loads(params["tags"]) == ["invoice", "reconciliation"]
    assert json.loads(params["metadata"]) == {"amount": 1000}


@pytest.mark.asyncio
async def test_search_queries_agent_memory_schema_and_maps_rows():
    now = datetime.datetime.now(datetime.timezone.utc)
    row = (
        "mem-1",
        "ws1",
        "finance_agent",
        "EPISODIC",
        "Invoice 123 reconciled",
        0.8,
        json.dumps(["invoice"]),
        json.dumps({"amount": 1000}),
        now,
    )
    session = _FakeSession(fetch_result=_FakeResult([row]))
    store = PostgresMemoryStore(db_session_factory=_session_factory(session))

    results = await store.search(workspace_id="ws1", agent_key="finance_agent", kind=MemoryKind.EPISODIC, limit=10)

    sql, params = session.executed[0]
    assert "FROM agent_memory.agent_memories" in sql
    assert params["workspace_id"] == "ws1"
    assert params["agent_key"] == "finance_agent"
    assert params["kind"] == "EPISODIC"
    assert len(results) == 1
    assert results[0].id == "mem-1"
    assert results[0].kind == MemoryKind.EPISODIC
    assert results[0].tags == ["invoice"]
    assert results[0].metadata == {"amount": 1000}


@pytest.mark.asyncio
async def test_delete_queries_agent_memory_schema():
    session = _FakeSession(fetch_result=_FakeResult([("mem-1",)]))
    store = PostgresMemoryStore(db_session_factory=_session_factory(session))

    await store.delete("mem-1")

    assert session.committed is True
    sql, params = session.executed[0]
    assert "DELETE FROM agent_memory.agent_memories WHERE id = :id RETURNING id;" in sql
    assert params["id"] == "mem-1"


@pytest.mark.asyncio
async def test_delete_missing_item_raises():
    session = _FakeSession(fetch_result=_FakeResult([]))
    store = PostgresMemoryStore(db_session_factory=_session_factory(session))

    with pytest.raises(MemoryNotFoundError):
        await store.delete("missing-mem")
