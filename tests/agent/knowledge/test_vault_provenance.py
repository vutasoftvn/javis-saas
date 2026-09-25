"""Task 2 (plan local-first-enterprise-knowledge) — knowledge đã "published"
phải trỏ về đúng 1 Vault document version cụ thể. Yêu cầu `AGENT_TEST_DATABASE_URL`
trỏ tới Postgres đã chạy migration 026/027 cho phần Postgres-backed; phần
validation ở PostgresKnowledgeStore.save_document tự nó không cần DB thật để
raise ValueError sớm (guard chạy trước session), nhưng test vẫn cần
db_session_factory hợp lệ theo constructor hiện tại nên vẫn skip nếu thiếu DB.
"""

from __future__ import annotations

import os
import uuid

import pytest
from agent.knowledge.models import KnowledgeDocument
from agent.knowledge.providers.postgres import PostgresKnowledgeStore
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

_RAW_DB_URL = os.environ.get("AGENT_TEST_DATABASE_URL")
if _RAW_DB_URL and "postgresql+asyncpg://" not in _RAW_DB_URL and "postgresql://" in _RAW_DB_URL:
    TEST_DATABASE_URL = _RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    TEST_DATABASE_URL = _RAW_DB_URL

pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="AGENT_TEST_DATABASE_URL not set")


@pytest.fixture
def postgres_knowledge_store():
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return PostgresKnowledgeStore(db_session_factory=factory)


@pytest.mark.asyncio
async def test_published_knowledge_requires_same_vault_version(postgres_knowledge_store):
    with pytest.raises(ValueError, match="vault_version_id"):
        await postgres_knowledge_store.save_document(
            KnowledgeDocument(workspace_id="ws-a", title="x", ingest_status="published")
        )


@pytest.mark.asyncio
async def test_non_published_knowledge_does_not_require_vault_version(postgres_knowledge_store):
    """Ingestion draft/review_pending KHÔNG bắt buộc phải từ Vault (không phải
    mọi knowledge source đều đi qua Vault) — chỉ trạng thái published mới cần
    provenance tường minh."""
    doc = KnowledgeDocument(
        id=f"doc_{uuid.uuid4().hex[:12]}",
        workspace_id=f"ws-{uuid.uuid4().hex[:8]}",
        title="Draft without vault link",
        ingest_status="review_pending",
    )
    await postgres_knowledge_store.save_document(doc)

    fetched = await postgres_knowledge_store.get_document(doc.id, doc.workspace_id)
    assert fetched is not None
    assert fetched.vault_version_id is None


@pytest.mark.asyncio
async def test_published_knowledge_with_vault_version_persists_provenance(postgres_knowledge_store):
    doc = KnowledgeDocument(
        id=f"doc_{uuid.uuid4().hex[:12]}",
        workspace_id=f"ws-{uuid.uuid4().hex[:8]}",
        title="Published with provenance",
        ingest_status="published",
        vault_document_id=str(uuid.uuid4()),
        vault_version_id=str(uuid.uuid4()),
        access_policy_version=1,
    )
    # vault_version_id không trỏ tới 1 vault.document_versions thật đang tồn tại
    # -> FK constraint (migration 027) phải reject, đúng ý nghĩa "provenance
    # phải xác thực được, không chỉ là 1 UUID bất kỳ".
    with pytest.raises(Exception, match=r"fk_knowledge_sources_vault_version|foreign key"):
        await postgres_knowledge_store.save_document(doc)
