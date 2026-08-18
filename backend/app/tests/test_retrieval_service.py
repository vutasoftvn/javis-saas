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
