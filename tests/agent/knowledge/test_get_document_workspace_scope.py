"""M3 §4 — get_document / update_document_ingest_status bind workspace."""

from __future__ import annotations

import pytest
from agent.knowledge.models import KnowledgeDocument
from agent.knowledge.service import KnowledgeIngestionService
from agent.knowledge.store import InMemoryKnowledgeStore


def _doc(ws: str, doc_id: str = "doc_1") -> KnowledgeDocument:
    return KnowledgeDocument(
        id=doc_id,
        workspace_id=ws,
        title="t",
        authority_class="USER_CONTENT",
        ingest_status="review_pending",
        chunks=[],
    )


@pytest.mark.asyncio
async def test_get_document_returns_none_for_other_workspace():
    store = InMemoryKnowledgeStore()
    await store.save_document(_doc("ws_a"))
    assert await store.get_document("doc_1", "ws_a") is not None
    assert await store.get_document("doc_1", "ws_b") is None


@pytest.mark.asyncio
async def test_update_ingest_status_rejects_cross_workspace():
    store = InMemoryKnowledgeStore()
    await store.save_document(_doc("ws_a"))
    svc = KnowledgeIngestionService(store)

    with pytest.raises(ValueError, match="not found"):
        await svc.update_document_ingest_status("doc_1", "published", "ws_b")

    # đúng workspace ⇒ ok
    updated = await svc.update_document_ingest_status("doc_1", "published", "ws_a")
    assert updated.ingest_status == "published"
