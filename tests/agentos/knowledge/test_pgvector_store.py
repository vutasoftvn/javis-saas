"""Test `PgVectorKnowledgeStore` with fake session verifying SQL, parameters,
schema qualification (`knowledge.*`), chunk versioning metadata, and fail-fast configuration.
"""
from __future__ import annotations

import datetime
import pytest

from agentos.knowledge.models import KnowledgeChunk, KnowledgeSource, KnowledgeSourceType
from agentos.knowledge.store import (
    ConfigurationError,
    KnowledgeSourceNotFoundError,
    PgVectorKnowledgeStore,
)


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
        PgVectorKnowledgeStore(db_session_factory=None)
    assert "requires a valid `db_session_factory`" in str(exc_info.value)


@pytest.mark.asyncio
async def test_put_source_inserts_with_correct_params_and_schema():
    session = _FakeSession()
    store = PgVectorKnowledgeStore(db_session_factory=_session_factory(session))
    source = KnowledgeSource(workspace_id="ws1", title="Doc", source_type=KnowledgeSourceType.POLICY)

    await store.put_source(source)

    assert session.committed is True
    sql, params = session.executed[0]
    assert "INSERT INTO knowledge.knowledge_sources" in sql
    assert params["id"] == source.id
    assert params["workspace_id"] == "ws1"
    assert params["source_type"] == "POLICY"


@pytest.mark.asyncio
async def test_put_chunks_inserts_one_row_per_chunk_with_versioning_metadata():
    session = _FakeSession()
    store = PgVectorKnowledgeStore(db_session_factory=_session_factory(session))
    chunks = [
        KnowledgeChunk(
            source_id="s1",
            workspace_id="ws1",
            chunk_index=0,
            content="a",
            embedding=[0.1, 0.2],
            embedding_model="text-embedding-3-small",
            embedding_dimensions=2,
            embedding_version="v1",
            content_hash="hash-a",
        ),
        KnowledgeChunk(
            source_id="s1",
            workspace_id="ws1",
            chunk_index=1,
            content="b",
            embedding=[0.3, 0.4],
            embedding_model="text-embedding-3-small",
            embedding_dimensions=2,
            embedding_version="v1",
            content_hash="hash-b",
        ),
    ]

    await store.put_chunks(chunks)

    assert len(session.executed) == 2
    assert session.committed is True
    for (sql, params), chunk in zip(session.executed, chunks):
        assert "INSERT INTO knowledge.knowledge_chunks" in sql
        assert params["embedding"] == f"[{','.join(repr(float(x)) for x in chunk.embedding)}]"
        assert params["embedding_model"] == "text-embedding-3-small"
        assert params["content_hash"] == chunk.content_hash


@pytest.mark.asyncio
async def test_put_chunks_with_empty_list_does_not_touch_the_session():
    session = _FakeSession()
    store = PgVectorKnowledgeStore(db_session_factory=_session_factory(session))

    await store.put_chunks([])

    assert session.executed == []


@pytest.mark.asyncio
async def test_search_uses_pgvector_cosine_distance_operator_and_maps_rows():
    now = datetime.datetime.now(datetime.timezone.utc)
    row = (
        "chunk-1",
        "source-1",
        "ws1",
        0,
        "some content",
        [0.1, 0.2],
        "text-embedding-3-small",
        2,
        "v1",
        "hash-1",
        now,
        "{}",
        0.87,
    )
    session = _FakeSession(fetch_result=_FakeResult([row]))
    store = PgVectorKnowledgeStore(db_session_factory=_session_factory(session))

    results = await store.search(workspace_id="ws1", query_embedding=[0.1, 0.2], limit=5)

    sql, params = session.executed[0]
    assert "<=>" in sql
    assert "FROM knowledge.knowledge_chunks" in sql
    assert params["workspace_id"] == "ws1"
    assert params["limit"] == 5
    assert len(results) == 1
    assert results[0].chunk.id == "chunk-1"
    assert results[0].chunk.embedding_model == "text-embedding-3-small"
    assert results[0].chunk.content_hash == "hash-1"
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

    assert "DELETE FROM knowledge.knowledge_sources" in session.executed[0][0]
    assert "DELETE FROM knowledge.knowledge_chunks" in session.executed[1][0]
    assert session.committed is True
