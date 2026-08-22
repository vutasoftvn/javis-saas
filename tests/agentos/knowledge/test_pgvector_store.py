"""Test `PgVectorKnowledgeStore` với 1 fake session (không cần Postgres/
pgvector thật — bảng `knowledge_sources`/`knowledge_chunks` chưa có
migration nào, xem docstring của chính class). Mục tiêu: xác nhận SQL/params
gửi đi đúng shape, không phải chạy tích hợp thật.
"""
from __future__ import annotations

import pytest

from agentos.knowledge.models import KnowledgeChunk, KnowledgeSource, KnowledgeSourceType
from agentos.knowledge.store import KnowledgeSourceNotFoundError, PgVectorKnowledgeStore


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
        self.executed.append((sql, params or {}))
        return self._fetch_result

    async def commit(self) -> None:
        self.committed = True

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *exc) -> None:
        return None


def _session_factory(session: _FakeSession):
    return lambda: session


@pytest.mark.asyncio
async def test_put_source_with_no_session_factory_is_a_noop():
    store = PgVectorKnowledgeStore()
    source = KnowledgeSource(workspace_id="ws1", title="Doc", source_type=KnowledgeSourceType.DOC)

    await store.put_source(source)  # không raise, không làm gì


@pytest.mark.asyncio
async def test_put_source_inserts_with_correct_params():
    session = _FakeSession()
    store = PgVectorKnowledgeStore(db_session_factory=_session_factory(session))
    source = KnowledgeSource(workspace_id="ws1", title="Doc", source_type=KnowledgeSourceType.POLICY)

    await store.put_source(source)

    assert session.committed is True
    sql, params = session.executed[0]
    assert "INSERT INTO knowledge_sources" in sql
    assert params["id"] == source.id
    assert params["workspace_id"] == "ws1"
    assert params["source_type"] == "POLICY"


@pytest.mark.asyncio
async def test_put_chunks_inserts_one_row_per_chunk():
    session = _FakeSession()
    store = PgVectorKnowledgeStore(db_session_factory=_session_factory(session))
    chunks = [
        KnowledgeChunk(source_id="s1", workspace_id="ws1", chunk_index=0, content="a", embedding=[0.1, 0.2]),
        KnowledgeChunk(source_id="s1", workspace_id="ws1", chunk_index=1, content="b", embedding=[0.3, 0.4]),
    ]

    await store.put_chunks(chunks)

    assert len(session.executed) == 2
    assert session.committed is True
    for (sql, params), chunk in zip(session.executed, chunks):
        assert "INSERT INTO knowledge_chunks" in sql
        assert params["embedding"] == chunk.embedding


@pytest.mark.asyncio
async def test_put_chunks_with_empty_list_does_not_touch_the_session():
    session = _FakeSession()
    store = PgVectorKnowledgeStore(db_session_factory=_session_factory(session))

    await store.put_chunks([])

    assert session.executed == []


@pytest.mark.asyncio
async def test_search_uses_pgvector_cosine_distance_operator_and_maps_rows():
    import datetime

    row = (
        "chunk-1",
        "source-1",
        "ws1",
        0,
        "some content",
        [0.1, 0.2],
        datetime.datetime.now(datetime.timezone.utc),
        "{}",
        0.87,
    )
    session = _FakeSession(fetch_result=_FakeResult([row]))
    store = PgVectorKnowledgeStore(db_session_factory=_session_factory(session))

    results = await store.search(workspace_id="ws1", query_embedding=[0.1, 0.2], limit=5)

    sql, params = session.executed[0]
    assert "<=>" in sql
    assert params["workspace_id"] == "ws1"
    assert params["limit"] == 5
    assert len(results) == 1
    assert results[0].chunk.id == "chunk-1"
    assert results[0].score == pytest.approx(0.87)


@pytest.mark.asyncio
async def test_delete_source_raises_when_not_found():
    session = _FakeSession(fetch_result=_FakeResult([]))
    store = PgVectorKnowledgeStore(db_session_factory=_session_factory(session))

    with pytest.raises(KnowledgeSourceNotFoundError):
        await store.delete_source("missing")


@pytest.mark.asyncio
async def test_delete_source_deletes_source_then_its_chunks():
    session = _FakeSession(fetch_result=_FakeResult([("source-1",)]))
    store = PgVectorKnowledgeStore(db_session_factory=_session_factory(session))

    await store.delete_source("source-1")

    assert "DELETE FROM knowledge_sources" in session.executed[0][0]
    assert "DELETE FROM knowledge_chunks" in session.executed[1][0]
    assert session.committed is True
