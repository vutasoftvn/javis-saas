from app.modules.vault.models import DocumentChunk


def test_document_chunk_ordinal_is_unique_within_a_revision():
    constraints = {constraint.name for constraint in DocumentChunk.__table__.constraints}

    assert "uq_document_chunks_revision_ordinal" in constraints
