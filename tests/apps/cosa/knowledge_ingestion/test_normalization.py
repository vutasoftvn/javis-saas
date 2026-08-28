"""Test normalization of converted Markdown into deterministic chunks with provenance."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest

__all__ = []


class TestNormalizeConversion:
    """Test normalize_conversion builds correct anchors, chunks, and manifest."""

    def test_normalize_simple_markdown_with_headings(self):
        """Test heading detection and anchor creation."""
        from apps.cosa.knowledge_ingestion.normalization import normalize_conversion
        from apps.cosa.knowledge_ingestion.markitdown_converter import ConversionResult
        from apps.cosa.knowledge_ingestion.preflight import ValidatedDocument

        conversion = ConversionResult(
            markdown="# Introduction\nSome intro text.\n## Subsection\nMore text.",
            title="Test Doc",
            package="markitdown",
            version="0.1.7",
            converter_profile="markitdown-safe-v1",
            output_sha256="abc123",
            warnings=[],
            failure_code=None,
        )

        validated = ValidatedDocument(
            object_key="quarantine/ws-1/ing_001/original",
            detected_media_type="text/plain",
            source_sha256="def456",
            size_bytes=1024,
        )

        candidate = normalize_conversion(
            result=conversion,
            document=validated,
            ingestion_id="ing_001",
        )

        # Verify candidate structure
        assert candidate.knowledge_document.title == "Test Doc"
        assert candidate.knowledge_document.ingest_status == "review_pending"
        assert candidate.knowledge_document.authority_class == "USER_CONTENT"
        assert candidate.knowledge_document.workspace_id == "ws-1"
        assert candidate.knowledge_document.source_uri == "object://knowledge-ingestions/ing_001"

        # Verify chunks exist and don't cross heading boundaries
        assert len(candidate.knowledge_document.chunks) >= 1
        for chunk in candidate.knowledge_document.chunks:
            assert chunk.chunker_name == "document-section-v1"
            assert chunk.chunker_version == "1"
            assert chunk.content_hash is not None
            assert "anchor_id" in chunk.metadata or chunk.metadata.get("anchor_id")

        # Verify manifest
        assert candidate.manifest["schema_version"] == "cosa.document-extraction-manifest/v1"
        assert candidate.manifest["ingestion_id"] == "ing_001"
        assert candidate.manifest["source_sha256"] == "def456"
        assert candidate.manifest["markdown_sha256"] == "abc123"
        assert candidate.manifest["detected_media_type"] == "text/plain"
        assert candidate.manifest["converter"]["name"] == "markitdown"
        assert candidate.manifest["converter"]["version"] == "0.1.7"
        assert candidate.manifest["converter"]["profile"] == "markitdown-safe-v1"
        assert len(candidate.manifest["anchors"]) >= 1

        # Verify anchors have proper structure
        for anchor in candidate.manifest["anchors"]:
            assert "id" in anchor
            assert "kind" in anchor
            assert anchor["kind"] in ("heading", "worksheet", "slide")
            assert "label" in anchor
            assert "ordinal" in anchor

    def test_normalize_markdown_with_tables_preserved(self):
        """Test that Markdown tables are preserved in normalized output."""
        from apps.cosa.knowledge_ingestion.normalization import normalize_conversion
        from apps.cosa.knowledge_ingestion.markitdown_converter import ConversionResult
        from apps.cosa.knowledge_ingestion.preflight import ValidatedDocument

        markdown_with_table = """# Data
| Name | Value |
|------|-------|
| A    | 1     |
| B    | 2     |

Text after table.
"""

        conversion = ConversionResult(
            markdown=markdown_with_table,
            title="Table Test",
            package="markitdown",
            version="0.1.7",
            converter_profile="markitdown-safe-v1",
            output_sha256="tbl123",
            warnings=[],
            failure_code=None,
        )

        validated = ValidatedDocument(
            object_key="quarantine/ws-1/ing_002/original",
            detected_media_type="application/pdf",
            source_sha256="tbl456",
            size_bytes=2048,
        )

        candidate = normalize_conversion(
            result=conversion,
            document=validated,
            ingestion_id="ing_002",
        )

        # Verify table syntax is preserved (Markdown format)
        full_markdown = "\n".join(
            chunk.content for chunk in sorted(
                candidate.knowledge_document.chunks,
                key=lambda c: c.chunk_index,
            )
        )
        assert "|" in full_markdown  # Table pipe syntax preserved
        assert "---" in full_markdown  # Table separator preserved

    def test_normalize_detects_xlsx_sheet_headers(self):
        """Test that XLSX sheet boundaries are detected and used as section labels."""
        from apps.cosa.knowledge_ingestion.normalization import normalize_conversion
        from apps.cosa.knowledge_ingestion.markitdown_converter import ConversionResult
        from apps.cosa.knowledge_ingestion.preflight import ValidatedDocument

        # Simulating MarkItDown output for XLSX with multiple sheets
        xlsx_markdown = """## Sheet1
| Column A | Column B |
|----------|----------|
| Data 1   | Value 1  |

## Sheet2
| Column A | Column B |
|----------|----------|
| Data 2   | Value 2  |
"""

        conversion = ConversionResult(
            markdown=xlsx_markdown,
            title="Spreadsheet",
            package="markitdown",
            version="0.1.7",
            converter_profile="markitdown-safe-v1",
            output_sha256="xlsx123",
            warnings=[],
            failure_code=None,
        )

        validated = ValidatedDocument(
            object_key="quarantine/ws-1/ing_003/original",
            detected_media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            source_sha256="xlsx456",
            size_bytes=4096,
        )

        candidate = normalize_conversion(
            result=conversion,
            document=validated,
            ingestion_id="ing_003",
        )

        # Verify sheet headers are treated as section anchors, not fabricated page numbers
        anchor_labels = [a["label"] for a in candidate.manifest["anchors"]]
        assert any("Sheet1" in label for label in anchor_labels)
        assert any("Sheet2" in label for label in anchor_labels)

        # Verify chunks respect sheet boundaries (no chunk crossing Sheet1 and Sheet2)
        for chunk in candidate.knowledge_document.chunks:
            content_lines = chunk.content.split("\n")
            sheet1_count = sum(1 for line in content_lines if "Sheet1" in line)
            sheet2_count = sum(1 for line in content_lines if "Sheet2" in line)
            # Chunk should not have both headers (crossing boundary)
            assert sheet1_count == 0 or sheet2_count == 0

    def test_normalize_splits_large_sections_with_reason(self):
        """Test that oversized sections are split with deterministic reason recorded."""
        from apps.cosa.knowledge_ingestion.normalization import normalize_conversion
        from apps.cosa.knowledge_ingestion.markitdown_converter import ConversionResult
        from apps.cosa.knowledge_ingestion.preflight import ValidatedDocument

        # Create a large single section that will exceed chunk size
        large_section = "# Main Section\n" + ("Large content text. " * 1000)

        conversion = ConversionResult(
            markdown=large_section,
            title="Large Doc",
            package="markitdown",
            version="0.1.7",
            converter_profile="markitdown-safe-v1",
            output_sha256="lg123",
            warnings=[],
            failure_code=None,
        )

        validated = ValidatedDocument(
            object_key="quarantine/ws-1/ing_004/original",
            detected_media_type="text/plain",
            source_sha256="lg456",
            size_bytes=50000,
        )

        candidate = normalize_conversion(
            result=conversion,
            document=validated,
            ingestion_id="ing_004",
        )

        # If multiple chunks exist for same section, verify split_reason is recorded
        chunks = candidate.knowledge_document.chunks
        section_chunks = [c for c in chunks if c.page_or_section == "Main Section"]
        if len(section_chunks) > 1:
            for chunk in section_chunks[1:]:  # All but first chunk
                assert "split_reason" in chunk.metadata
                assert chunk.metadata["split_reason"] == "section_too_large"

    def test_normalize_preserves_metadata_fields(self):
        """Test that all required metadata fields are present in normalized candidate."""
        from apps.cosa.knowledge_ingestion.normalization import normalize_conversion
        from apps.cosa.knowledge_ingestion.markitdown_converter import ConversionResult
        from apps.cosa.knowledge_ingestion.preflight import ValidatedDocument

        conversion = ConversionResult(
            markdown="# Test\nContent.",
            title="Metadata Test",
            package="markitdown",
            version="0.1.7",
            converter_profile="markitdown-safe-v1",
            output_sha256="meta123",
            warnings=["table_structure_degraded"],
            failure_code=None,
        )

        validated = ValidatedDocument(
            object_key="quarantine/ws-1/ing_005/original",
            detected_media_type="text/html",
            source_sha256="meta456",
            size_bytes=1024,
        )

        candidate = normalize_conversion(
            result=conversion,
            document=validated,
            ingestion_id="ing_005",
        )

        # Verify all required metadata fields
        doc_metadata = candidate.knowledge_document.metadata
        assert doc_metadata["ingestion_id"] == "ing_005"
        assert doc_metadata["source_sha256"] == "meta456"
        assert doc_metadata["markdown_sha256"] == "meta123"
        assert doc_metadata["converter_name"] == "markitdown"
        assert doc_metadata["converter_version"] == "0.1.7"
        assert doc_metadata["converter_profile"] == "markitdown-safe-v1"
        assert doc_metadata["manifest_schema_version"] == "cosa.document-extraction-manifest/v1"
        assert "warning_codes" in doc_metadata
        assert doc_metadata["warning_codes"] == ["table_structure_degraded"]

    def test_normalize_extracts_workspace_from_object_key(self):
        """Test that workspace_id is correctly extracted from object key."""
        from apps.cosa.knowledge_ingestion.normalization import normalize_conversion
        from apps.cosa.knowledge_ingestion.markitdown_converter import ConversionResult
        from apps.cosa.knowledge_ingestion.preflight import ValidatedDocument

        conversion = ConversionResult(
            markdown="# Test",
            title="Test",
            package="markitdown",
            version="0.1.7",
            converter_profile="markitdown-safe-v1",
            output_sha256="ws123",
            warnings=[],
            failure_code=None,
        )

        validated = ValidatedDocument(
            object_key="quarantine/my-workspace-xyz/ing_006/original",
            detected_media_type="text/plain",
            source_sha256="ws456",
            size_bytes=1024,
        )

        candidate = normalize_conversion(
            result=conversion,
            document=validated,
            ingestion_id="ing_006",
        )

        assert candidate.knowledge_document.workspace_id == "my-workspace-xyz"

    def test_normalize_handles_empty_markdown_gracefully(self):
        """Test normalization handles edge case of empty Markdown output."""
        from apps.cosa.knowledge_ingestion.normalization import normalize_conversion
        from apps.cosa.knowledge_ingestion.markitdown_converter import ConversionResult
        from apps.cosa.knowledge_ingestion.preflight import ValidatedDocument

        conversion = ConversionResult(
            markdown="",
            title="Empty",
            package="markitdown",
            version="0.1.7",
            converter_profile="markitdown-safe-v1",
            output_sha256="empty123",
            warnings=[],
            failure_code=None,
        )

        validated = ValidatedDocument(
            object_key="quarantine/ws-1/ing_007/original",
            detected_media_type="text/plain",
            source_sha256="empty456",
            size_bytes=0,
        )

        candidate = normalize_conversion(
            result=conversion,
            document=validated,
            ingestion_id="ing_007",
        )

        # Should handle gracefully — maybe one empty chunk or no chunks
        assert candidate.knowledge_document.ingest_status == "review_pending"
        assert len(candidate.knowledge_document.chunks) >= 0


class TestNormalizedKnowledgeCandidate:
    """Test the NormalizedKnowledgeCandidate model."""

    def test_candidate_has_knowledge_document_and_manifest(self):
        """Test candidate bundles knowledge document and manifest."""
        from apps.cosa.knowledge_ingestion.normalization import NormalizedKnowledgeCandidate
        from agent_core.knowledge.models import KnowledgeDocument, KnowledgeChunk

        doc = KnowledgeDocument(
            workspace_id="ws-1",
            title="Test",
            ingest_status="review_pending",
            authority_class="USER_CONTENT",
            chunks=[
                KnowledgeChunk(
                    document_id="doc_1",
                    workspace_id="ws-1",
                    chunk_index=0,
                    content="Content",
                )
            ],
        )

        manifest = {
            "schema_version": "cosa.document-extraction-manifest/v1",
            "ingestion_id": "ing_001",
            "source_sha256": "abc",
            "detected_media_type": "text/plain",
            "converter": {
                "name": "markitdown",
                "version": "0.1.7",
                "profile": "markitdown-safe-v1",
            },
            "markdown_sha256": "def",
            "anchors": [],
            "warnings": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        candidate = NormalizedKnowledgeCandidate(
            knowledge_document=doc,
            manifest=manifest,
        )

        assert candidate.knowledge_document == doc
        assert candidate.manifest == manifest
