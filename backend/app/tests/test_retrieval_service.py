from datetime import date, timedelta

import pytest
from sqlalchemy.dialects import postgresql

from app.platform.vault import retrieval_service


class _FakeResult:
    def __iter__(self):
        return iter(())


class _FakeSession:
    def __init__(self):
        self.captured_sql = None
        self.captured_params = None

    def execute(self, sql, params):
        self.captured_sql = sql
        self.captured_params = params
        return _FakeResult()


@pytest.mark.asyncio
async def test_search_chunks_binds_query_embedding_before_vector_cast(monkeypatch):
    """:query_embedding immediately followed by ::vector (no space) is not
    recognized as a bind parameter by SQLAlchemy's text() parser, so it is
    left as literal text and Postgres rejects the query with a syntax error
    at the ':'. Every RAG-enabled chat turn fails as a result."""

    async def fake_generate_embeddings(texts):
        return [[0.0, 0.1, 0.2]]

    monkeypatch.setattr(retrieval_service, "generate_embeddings", fake_generate_embeddings)

    db = _FakeSession()
    await retrieval_service.search_chunks(db, brain_id=1, query="hello")

    compiled = db.captured_sql.compile(dialect=postgresql.dialect(paramstyle="pyformat"))
    assert ":query_embedding" not in str(compiled), (
        f"query_embedding bind param was not substituted: {compiled}"
    )


@pytest.mark.asyncio
async def test_search_chunks_passes_stage_and_dimension_as_bind_params(monkeypatch):
    """Không filter khi caller không truyền gì (backward-compatible với
    chat_execution_service._retrieve_context hiện tại), nhưng khi có thì phải đi vào params
    chứ không phải nối chuỗi trực tiếp vào SQL."""

    async def fake_generate_embeddings(texts):
        return [[0.0, 0.1, 0.2]]

    monkeypatch.setattr(retrieval_service, "generate_embeddings", fake_generate_embeddings)

    db = _FakeSession()
    await retrieval_service.search_chunks(db, brain_id=1, query="hello", stage="S1_PROBLEM_VALIDATION", dimension="PROBLEM")

    assert db.captured_params["stage"] == "S1_PROBLEM_VALIDATION"
    assert db.captured_params["dimension"] == "PROBLEM"


@pytest.mark.asyncio
async def test_search_chunks_defaults_stage_and_dimension_to_none(monkeypatch):
    async def fake_generate_embeddings(texts):
        return [[0.0, 0.1, 0.2]]

    monkeypatch.setattr(retrieval_service, "generate_embeddings", fake_generate_embeddings)

    db = _FakeSession()
    await retrieval_service.search_chunks(db, brain_id=1, query="hello")

    assert db.captured_params["stage"] is None
    assert db.captured_params["dimension"] is None


def test_is_stale_ignores_non_regulatory_documents():
    assert retrieval_service._is_stale(False, None) is False
    assert retrieval_service._is_stale(False, date(2020, 1, 1)) is False


def test_is_stale_treats_a_regulatory_document_with_no_verification_date_as_stale():
    assert retrieval_service._is_stale(True, None) is True


def test_is_stale_flags_a_regulatory_document_past_the_threshold():
    old_date = date.today() - timedelta(days=retrieval_service.REGULATORY_STALE_THRESHOLD_DAYS + 1)
    assert retrieval_service._is_stale(True, old_date) is True


def test_is_stale_trusts_a_recently_verified_regulatory_document():
    recent_date = date.today() - timedelta(days=1)
    assert retrieval_service._is_stale(True, recent_date) is False
