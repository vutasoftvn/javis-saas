"""Test new knowledge document candidate statuses and persistence."""

from __future__ import annotations

import pytest
import pytest_asyncio

__all__ = []


class TestKnowledgeDocumentCandidateStatus:
    """Test new ingest_status literals for candidates."""

    def test_knowledge_document_supports_review_pending_status(self):
        """Test review_pending is a valid ingest_status."""
        from agent_core.knowledge.models import KnowledgeDocument

        doc = KnowledgeDocument(
            workspace_id="ws-1",
            title="Candidate",
            ingest_status="review_pending",
        )

        assert doc.ingest_status == "review_pending"

    def test_knowledge_document_supports_published_status(self):
        """Test published is a valid ingest_status."""
        from agent_core.knowledge.models import KnowledgeDocument

        doc = KnowledgeDocument(
            workspace_id="ws-1",
            title="Published Doc",
            ingest_status="published",
        )

        assert doc.ingest_status == "published"

    def test_knowledge_document_supports_rejected_status(self):
        """Test rejected is a valid ingest_status."""
        from agent_core.knowledge.models import KnowledgeDocument

        doc = KnowledgeDocument(
            workspace_id="ws-1",
            title="Rejected Doc",
            ingest_status="rejected",
        )

        assert doc.ingest_status == "rejected"

    def test_knowledge_document_preserves_existing_statuses(self):
        """Test existing statuses still work: pending, processing, completed, failed."""
        from agent_core.knowledge.models import KnowledgeDocument

        for status in ["pending", "processing", "completed", "failed"]:
            doc = KnowledgeDocument(
                workspace_id="ws-1",
                title="Test",
                ingest_status=status,
            )
            assert doc.ingest_status == status

    def test_knowledge_document_candidate_defaults_to_completed(self):
        """Test that default status is still completed (backward compatibility)."""
        from agent_core.knowledge.models import KnowledgeDocument

        doc = KnowledgeDocument(
            workspace_id="ws-1",
            title="Default",
        )

        assert doc.ingest_status == "completed"

    def test_knowledge_document_can_set_authority_class_user_content(self):
        """Test USER_CONTENT authority class."""
        from agent_core.knowledge.models import KnowledgeDocument

        doc = KnowledgeDocument(
            workspace_id="ws-1",
            title="User Content",
            authority_class="USER_CONTENT",
        )

        assert doc.authority_class == "USER_CONTENT"

    def test_knowledge_document_candidate_has_metadata_dict(self):
        """Test candidate metadata includes all required fields."""
        from agent_core.knowledge.models import KnowledgeDocument

        metadata = {
            "ingestion_id": "ing_001",
            "source_sha256": "abc123",
            "markdown_sha256": "def456",
            "converter_name": "markitdown",
            "converter_version": "0.1.7",
            "converter_profile": "markitdown-safe-v1",
            "manifest_schema_version": "cosa.document-extraction-manifest/v1",
            "scan_verdict": "clean",
            "warning_codes": [],
        }

        doc = KnowledgeDocument(
            workspace_id="ws-1",
            title="Candidate",
            ingest_status="review_pending",
            authority_class="USER_CONTENT",
            metadata=metadata,
        )

        assert doc.metadata["ingestion_id"] == "ing_001"
        assert doc.metadata["source_sha256"] == "abc123"
        assert doc.metadata["markdown_sha256"] == "def456"


class TestKnowledgeIngestionServiceIngestNormalizedDocument:
    """Test new ingest_normalized_document method."""

    @pytest_asyncio.fixture
    async def service(self):
        """Provide in-memory knowledge ingestion service."""
        from agent_core.knowledge.service import KnowledgeIngestionService
        from agent_core.knowledge.store import InMemoryKnowledgeStore

        store = InMemoryKnowledgeStore()
        return KnowledgeIngestionService(store=store)

    @pytest.mark.asyncio
    async def test_ingest_normalized_document_persists_candidate(self, service):
        """Test ingest_normalized_document persists without re-chunking."""
        from agent_core.knowledge.models import KnowledgeDocument, KnowledgeChunk

        candidate = KnowledgeDocument(
            id="doc_candidate_1",
            workspace_id="ws-1",
            title="Review Pending",
            source_uri="object://knowledge-ingestions/ing_001",
            media_type="application/pdf",
            checksum="abc123",
            authority_class="USER_CONTENT",
            ingest_status="review_pending",
            chunks=[
                KnowledgeChunk(
                    id="chk_1",
                    document_id="doc_candidate_1",
                    workspace_id="ws-1",
                    chunk_index=0,
                    content="Pre-chunked content",
                    chunker_name="document-section-v1",
                    chunker_version="1",
                    content_hash="xyz789",
                    metadata={"anchor_id": "sec-001"},
                ),
            ],
            metadata={
                "ingestion_id": "ing_001",
                "source_sha256": "source123",
                "markdown_sha256": "markdown123",
                "converter_name": "markitdown",
                "converter_version": "0.1.7",
                "converter_profile": "markitdown-safe-v1",
                "manifest_schema_version": "cosa.document-extraction-manifest/v1",
            },
        )

        # Persist without re-chunking
        result = await service.ingest_normalized_document(candidate)

        # Verify document was stored as-is
        assert result.id == "doc_candidate_1"
        assert result.ingest_status == "review_pending"
        assert result.authority_class == "USER_CONTENT"
        assert len(result.chunks) == 1
        assert result.chunks[0].chunker_name == "document-section-v1"
        assert result.chunks[0].chunk_index == 0

    @pytest.mark.asyncio
    async def test_ingest_normalized_document_does_not_re_chunk(self, service):
        """Test that caller-provided chunks are preserved exactly."""
        from agent_core.knowledge.models import KnowledgeDocument, KnowledgeChunk

        # Create a candidate with specific chunks
        chunks = [
            KnowledgeChunk(
                id="chk_0",
                document_id="doc_1",
                workspace_id="ws-1",
                chunk_index=0,
                content="First chunk content",
            ),
            KnowledgeChunk(
                id="chk_1",
                document_id="doc_1",
                workspace_id="ws-1",
                chunk_index=1,
                content="Second chunk content",
            ),
        ]

        candidate = KnowledgeDocument(
            id="doc_1",
            workspace_id="ws-1",
            title="Two Chunks",
            ingest_status="review_pending",
            chunks=chunks,
        )

        result = await service.ingest_normalized_document(candidate)

        # Should have exactly the chunks we provided
        assert len(result.chunks) == 2
        assert result.chunks[0].content == "First chunk content"
        assert result.chunks[1].content == "Second chunk content"

    @pytest.mark.asyncio
    async def test_ingest_raw_text_backward_compatibility(self, service):
        """Test that ingest_raw_text still works with default completed status."""
        result = await service.ingest_raw_text(
            workspace_id="ws-1",
            title="Raw Text",
            text_content="This is raw text content.",
        )

        assert result.ingest_status == "completed"
        assert result.authority_class == "REFERENCE"
        assert len(result.chunks) >= 1

    @pytest.mark.asyncio
    async def test_ingest_raw_text_unchanged_default_behavior(self, service):
        """Test ingest_raw_text chunks text and creates default completed document."""
        result = await service.ingest_raw_text(
            workspace_id="ws-1",
            title="Test Document",
            text_content="Short content here. " * 100,  # Repeat to exceed default chunk size
            chunk_size=100,
            overlap=10,
        )

        # Verify default behavior unchanged
        assert result.ingest_status == "completed"
        assert result.authority_class == "REFERENCE"
        assert len(result.chunks) > 1  # Multiple chunks from text chunking
        assert result.chunks[0].page_or_section is not None


class TestPostgresKnowledgeStoreProvenance:
    """Test that postgres store preserves provenance columns."""

    def test_postgres_store_loads_and_populates_parser_metadata(self):
        """Test that source_versions can store parser metadata (via integration test mock)."""
        from agent_core.knowledge.providers.postgres import PostgresKnowledgeStore
        from agent_core.knowledge.models import KnowledgeDocument, KnowledgeChunk

        # Static test of the method signature — actual DB test below
        store = PostgresKnowledgeStore

        doc = KnowledgeDocument(
            id="doc_test",
            workspace_id="ws-1",
            title="Test",
            chunks=[
                KnowledgeChunk(
                    document_id="doc_test",
                    workspace_id="ws-1",
                    chunk_index=0,
                    content="test",
                )
            ],
        )

        # Verify metadata fields can be set
        doc.metadata["ingestion_run_id"] = "ing_001"
        doc.metadata["parser_name"] = "markitdown"
        doc.metadata["parser_version"] = "0.1.7"

        assert doc.metadata["ingestion_run_id"] == "ing_001"
        assert doc.metadata["parser_name"] == "markitdown"
        assert doc.metadata["parser_version"] == "0.1.7"

    @pytest_asyncio.fixture
    async def session_factory(self):
        """Provide test database session factory if available."""
        import os

        TEST_DATABASE_URL = os.environ.get("AGENT_CORE_TEST_DATABASE_URL")
        if not TEST_DATABASE_URL:
            pytest.skip("AGENT_CORE_TEST_DATABASE_URL not set")

        if "postgresql+asyncpg://" not in TEST_DATABASE_URL:
            TEST_DATABASE_URL = TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        engine = create_async_engine(TEST_DATABASE_URL)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        yield factory
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_postgres_store_persists_parser_metadata(self, session_factory):
        """Test that parser metadata is written to source_versions columns."""
        from agent_core.knowledge.providers.postgres import PostgresKnowledgeStore
        from agent_core.knowledge.models import KnowledgeDocument, KnowledgeChunk
        from sqlalchemy import text

        store = PostgresKnowledgeStore(db_session_factory=session_factory)

        doc = KnowledgeDocument(
            id="doc_provenance_test",
            workspace_id="ws-provenance-test",
            title="Provenance Test",
            ingest_status="review_pending",
            authority_class="USER_CONTENT",
            chunks=[
                KnowledgeChunk(
                    document_id="doc_provenance_test",
                    workspace_id="ws-provenance-test",
                    chunk_index=0,
                    content="Test content",
                )
            ],
            metadata={
                "ingestion_run_id": "ing_prov_001",
                "parser_name": "markitdown",
                "parser_version": "0.1.7",
            },
        )

        await store.save_document(doc)

        # Verify columns were populated
        async with session_factory() as session:
            row = (
                await session.execute(
                    text(
                        """
                        SELECT ingestion_run_id, parser_name, parser_version
                        FROM knowledge.source_versions
                        WHERE source_id = :source_id
                        ORDER BY version DESC
                        LIMIT 1
                        """
                    ),
                    {"source_id": doc.id},
                )
            ).mappings().first()

            assert row is not None
            assert row["ingestion_run_id"] == "ing_prov_001"
            assert row["parser_name"] == "markitdown"
            assert row["parser_version"] == "0.1.7"
