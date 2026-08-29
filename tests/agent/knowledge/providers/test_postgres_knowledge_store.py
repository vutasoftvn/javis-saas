"""Wave 8 — PostgresKnowledgeStore (Blueprint V2 §27, migration 010). Trước
Wave 8 KHÔNG có implementation Postgres nào cho KnowledgeStore dù schema
knowledge.knowledge_sources/knowledge_chunks đã tồn tại từ migration 003 —
schema có nhưng không ai ghi/đọc qua đó. I/O test thật cần
AGENT_TEST_DATABASE_URL (skip nếu không set, giống test_postgres_store.py
của memory); phần logic không cần DB (content hash, config error) test được
trực tiếp."""
from __future__ import annotations

import os

import pytest
import pytest_asyncio

pytest.importorskip("asyncpg")

_RAW_DB_URL = os.environ.get("AGENT_TEST_DATABASE_URL")
if _RAW_DB_URL and "postgresql+asyncpg://" not in _RAW_DB_URL and "postgresql://" in _RAW_DB_URL:
    TEST_DATABASE_URL = _RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    TEST_DATABASE_URL = _RAW_DB_URL


def test_postgres_knowledge_store_requires_session_factory():
    from agent.knowledge.providers.postgres import ConfigurationError, PostgresKnowledgeStore

    with pytest.raises(ConfigurationError):
        PostgresKnowledgeStore(db_session_factory=None)


def test_compute_document_content_hash_is_deterministic_and_order_independent_by_index():
    from agent.knowledge.models import KnowledgeChunk, KnowledgeDocument
    from agent.knowledge.providers.postgres import PostgresKnowledgeStore

    doc = KnowledgeDocument(
        workspace_id="ws-1",
        title="Test Doc",
        chunks=[
            KnowledgeChunk(document_id="d1", workspace_id="ws-1", chunk_index=1, content="phần hai"),
            KnowledgeChunk(document_id="d1", workspace_id="ws-1", chunk_index=0, content="phần một"),
        ],
    )

    hash1 = PostgresKnowledgeStore._compute_document_content_hash(doc)
    hash2 = PostgresKnowledgeStore._compute_document_content_hash(doc)
    assert hash1 == hash2  # deterministic

    # Đổi nội dung 1 chunk -> hash phải đổi (phát hiện được version mới cần tạo).
    doc.chunks[0].content = "phần hai đã sửa"
    hash3 = PostgresKnowledgeStore._compute_document_content_hash(doc)
    assert hash3 != hash1


def test_knowledge_document_defaults_authority_class_reference():
    from agent.knowledge.models import KnowledgeDocument

    doc = KnowledgeDocument(workspace_id="ws-1", title="Untitled")
    assert doc.authority_class == "REFERENCE"


@pytest_asyncio.fixture
async def session_factory():
    if not TEST_DATABASE_URL:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_save_and_get_document_roundtrip_with_source_versioning(session_factory):
    from agent.knowledge.models import KnowledgeChunk, KnowledgeDocument
    from agent.knowledge.providers.postgres import PostgresKnowledgeStore

    store = PostgresKnowledgeStore(db_session_factory=session_factory)
    doc = KnowledgeDocument(
        workspace_id="ws-knowledge-test",
        title="Company Handbook",
        authority_class="POLICY",
        chunks=[
            KnowledgeChunk(document_id="placeholder", workspace_id="ws-knowledge-test", chunk_index=0, content="Điều khoản 1"),
        ],
    )
    doc.chunks[0].document_id = doc.id
    await store.save_document(doc)

    fetched = await store.get_document(doc.id, "ws-knowledge-test")
    assert fetched is not None
    assert fetched.title == "Company Handbook"
    assert fetched.authority_class == "POLICY"
    assert len(fetched.chunks) == 1
    assert fetched.chunks[0].content == "Điều khoản 1"

    # Save lại với nội dung khác -> phải tạo source_version mới (v2), không mất v1.
    doc.chunks[0].content = "Điều khoản 1 (đã cập nhật)"
    await store.save_document(doc)

    async with session_factory() as session:
        from sqlalchemy import text

        rows = (
            await session.execute(
                text("SELECT version FROM knowledge.source_versions WHERE source_id = :id ORDER BY version"),
                {"id": doc.id},
            )
        ).mappings().all()
        assert [r["version"] for r in rows] == [1, 2]
