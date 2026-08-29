"""P1 Task 6: retrieval có gate eval. Semantic chỉ chạy khi eval score đạt
ngưỡng VÀ có query embedding VÀ store hỗ trợ; ngược lại fallback lexical,
luôn kèm citations trỏ đúng workspace."""
import pytest

from agent.knowledge.models import KnowledgeChunk, KnowledgeDocument
from agent.knowledge.retrieval import KnowledgeRetrievalConfig, retrieve
from agent.knowledge.store import InMemoryKnowledgeStore

pytestmark = pytest.mark.asyncio


async def _seed(store, workspace_id, doc_id, text, embedding=None):
    doc = KnowledgeDocument(
        id=doc_id, workspace_id=workspace_id, title=f"Doc {doc_id}",
        chunks=[KnowledgeChunk(
            id=f"chk_{doc_id}", document_id=doc_id, workspace_id=workspace_id,
            chunk_index=0, content=text, embedding=embedding,
        )],
    )
    await store.save_document(doc)


async def test_semantic_below_threshold_falls_back_to_lexical_with_citations():
    store = InMemoryKnowledgeStore()
    await _seed(store, "ws_1", "d_a", "quarterly revenue grew twelve percent")
    cfg = KnowledgeRetrievalConfig(mode="semantic", min_eval_score=0.8)
    res = await retrieve(store, cfg, workspace_id="ws_1", query="revenue",
                         limit=5, eval_score=0.5, query_embedding=[0.1, 0.2])
    assert res.mode_used == "lexical" and res.fell_back is True
    assert res.citations and all(c.document_id == "d_a" for c in res.citations)


async def test_semantic_used_when_eval_meets_threshold_and_embedding_present():
    store = InMemoryKnowledgeStore()
    await _seed(store, "ws_1", "d_a", "alpha beta", embedding=[1.0, 0.0])
    await _seed(store, "ws_1", "d_b", "gamma delta", embedding=[0.0, 1.0])
    cfg = KnowledgeRetrievalConfig(mode="semantic", min_eval_score=0.8)
    res = await retrieve(store, cfg, workspace_id="ws_1", query="anything",
                         limit=1, eval_score=0.9, query_embedding=[0.95, 0.05])
    assert res.mode_used == "semantic" and res.fell_back is False
    assert res.citations[0].document_id == "d_a"


async def test_semantic_without_query_embedding_falls_back():
    store = InMemoryKnowledgeStore()
    await _seed(store, "ws_1", "d_a", "revenue report", embedding=[1.0, 0.0])
    cfg = KnowledgeRetrievalConfig(mode="semantic", min_eval_score=0.5)
    res = await retrieve(store, cfg, workspace_id="ws_1", query="revenue",
                         limit=5, eval_score=0.9, query_embedding=None)
    assert res.mode_used == "lexical" and res.fell_back is True


async def test_lexical_mode_never_reports_fallback():
    store = InMemoryKnowledgeStore()
    await _seed(store, "ws_1", "d_a", "revenue report")
    res = await retrieve(store, KnowledgeRetrievalConfig(mode="lexical"),
                         workspace_id="ws_1", query="revenue", limit=5, eval_score=None)
    assert res.mode_used == "lexical" and res.fell_back is False


async def test_citations_are_workspace_scoped():
    store = InMemoryKnowledgeStore()
    await _seed(store, "ws_1", "d_1", "shared term alpha")
    await _seed(store, "ws_2", "d_2", "shared term alpha")
    res = await retrieve(store, KnowledgeRetrievalConfig(mode="lexical"),
                         workspace_id="ws_1", query="alpha", limit=10, eval_score=None)
    assert {c.document_id for c in res.citations} == {"d_1"}
