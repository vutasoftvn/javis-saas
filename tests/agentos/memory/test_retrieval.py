import pytest

from agentos.memory.retrieval import MemoryQuery, score_relevance


def test_score_relevance_full_overlap_is_one():
    assert score_relevance("hit target revenue", "hit target revenue") == 1.0


def test_score_relevance_partial_overlap():
    assert score_relevance("hit target revenue", "hit target churn") == pytest.approx(2 / 3)


def test_score_relevance_no_overlap_is_zero():
    assert score_relevance("hit target revenue", "completely unrelated text") == 0.0


def test_score_relevance_empty_content_is_zero():
    assert score_relevance("hit target revenue", "") == 0.0


def test_score_relevance_is_case_insensitive():
    assert score_relevance("Hit Target", "hit target") == 1.0


def test_memory_query_defaults_limit():
    query = MemoryQuery(workspace_id="ws1", agent_key="a1", text="hi")
    assert query.limit == 20
