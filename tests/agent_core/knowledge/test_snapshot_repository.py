from __future__ import annotations

import pytest

from agent_core.knowledge.snapshot import KnowledgeSnapshot
from agent_core.knowledge.snapshot_repository import InMemoryKnowledgeSnapshotRepository
from agent_core.registry.repository import SpecVersionHashConflictError


def _snapshot(**overrides) -> KnowledgeSnapshot:
    base = dict(
        id="workspace-abc.default_kb",
        version="1",
        workspace_id="workspace-abc",
        embedding_model="text-embedding-3-small",
        embedding_version="1",
        source_refs=[{"source_id": "src_1", "version": 1, "content_hash": "a" * 64}],
    )
    base.update(overrides)
    return KnowledgeSnapshot(**base)


@pytest.mark.asyncio
async def test_publish_snapshot_is_immutable_and_idempotent():
    repo = InMemoryKnowledgeSnapshotRepository()
    snapshot = _snapshot()

    published1 = await repo.publish(snapshot)
    assert published1.definition_hash == snapshot.with_hash().definition_hash

    published2 = await repo.publish(snapshot)
    assert published2.definition_hash == published1.definition_hash

    changed = _snapshot(embedding_version="2")
    with pytest.raises(SpecVersionHashConflictError):
        await repo.publish(changed)


@pytest.mark.asyncio
async def test_get_returns_none_when_not_published():
    repo = InMemoryKnowledgeSnapshotRepository()

    result = await repo.get("does.not.exist", "1")

    assert result is None


@pytest.mark.asyncio
async def test_get_returns_full_content_after_publish():
    repo = InMemoryKnowledgeSnapshotRepository()
    snapshot = _snapshot()
    await repo.publish(snapshot)

    fetched = await repo.get("workspace-abc.default_kb", "1")

    assert fetched is not None
    assert fetched.source_refs == [{"source_id": "src_1", "version": 1, "content_hash": "a" * 64}]
    assert fetched.embedding_model == "text-embedding-3-small"


import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent_core.knowledge.snapshot_repository import PostgresKnowledgeSnapshotRepository

_RAW_DB_URL = os.environ.get("AGENT_CORE_TEST_DATABASE_URL")
if _RAW_DB_URL and "postgresql+asyncpg://" not in _RAW_DB_URL and "postgresql://" in _RAW_DB_URL:
    TEST_DATABASE_URL = _RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    TEST_DATABASE_URL = _RAW_DB_URL


def _pg_session_factory():
    if not TEST_DATABASE_URL:
        pytest.skip("AGENT_CORE_TEST_DATABASE_URL not set")
    engine = create_async_engine(TEST_DATABASE_URL)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="AGENT_CORE_TEST_DATABASE_URL not set")
@pytest.mark.asyncio
async def test_postgres_knowledge_snapshot_repository_publish_and_get_roundtrip():
    repo = PostgresKnowledgeSnapshotRepository(_pg_session_factory())
    snapshot = _snapshot(id="test.knowledge_snapshot.pg_1", version="1")

    published = await repo.publish(snapshot)
    fetched = await repo.get("test.knowledge_snapshot.pg_1", "1")

    assert fetched is not None
    assert fetched.definition_hash == published.definition_hash
    assert fetched.source_refs == [{"source_id": "src_1", "version": 1, "content_hash": "a" * 64}]


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="AGENT_CORE_TEST_DATABASE_URL not set")
@pytest.mark.asyncio
async def test_postgres_knowledge_snapshot_repository_rejects_hash_conflict():
    repo = PostgresKnowledgeSnapshotRepository(_pg_session_factory())
    snapshot = _snapshot(id="test.knowledge_snapshot.pg_2", version="1")
    await repo.publish(snapshot)

    changed = _snapshot(id="test.knowledge_snapshot.pg_2", version="1", embedding_version="99")
    with pytest.raises(SpecVersionHashConflictError):
        await repo.publish(changed)

