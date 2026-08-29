from __future__ import annotations

import pytest

from agent.knowledge import (
    InMemoryKnowledgeStore,
    KnowledgeIngestionService,
    chunk_text,
)


def test_chunk_text_algorithm():
    text = "Hello world! " * 100
    chunks = chunk_text(text, chunk_size=200, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)


@pytest.mark.asyncio
async def test_promoted_knowledge_ingestion_and_retrieval():
    """Kiểm thử Promoted Knowledge Subsystem (§26 & §43.10)."""
    store = InMemoryKnowledgeStore()
    svc = KnowledgeIngestionService(store)

    content = """
    # Company Payout Policy 2026
    All vendor payouts above $10,000 must be approved by the Chief Financial Officer.
    All payments below $1,000 can be processed automatically by the Operations Lead.
    Tax withholding must follow local circular 111/2013/TT-BTC guidelines.
    """

    doc = await svc.ingest_raw_text(
        workspace_id="ws_101",
        title="Payout Policy 2026",
        text_content=content,
        source_uri="https://docs.company.internal/payout_policy.md",
        chunk_size=150,
        overlap=30,
    )

    assert doc.id.startswith("doc_")
    assert len(doc.chunks) >= 2

    # Tìm kiếm trích dẫn
    citations = await svc.retrieve_citations(
        workspace_id="ws_101",
        query="Chief Financial Officer payouts approval",
        limit=2,
    )

    assert len(citations) >= 1
    assert "Chief Financial Officer" in citations[0].snippet
    assert citations[0].document_title == "Payout Policy 2026"
