"""Normalize converted Markdown into deterministic chunks with provenance.

Điểm này chịu trách nhiệm chuẩn hoá output từ converter (Markdown, title, warnings)
thành KnowledgeDocument/KnowledgeChunk để agent lưu trữ. Tách biệt logic
của app từ logic lưu trữ của core.

Không phải lệnh xuất khẩu của agent hoặc model — đây là deterministic normalization
của dữ liệu đã qua converter + preflight, đặt sẵn trạng thái review_pending.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from agent.knowledge.models import KnowledgeChunk, KnowledgeDocument

from apps.cosa.knowledge_ingestion.markitdown_converter import ConversionResult
from apps.cosa.knowledge_ingestion.preflight import ValidatedDocument

__all__ = [
    "DocumentExtractionManifest",
    "NormalizedKnowledgeCandidate",
    "normalize_conversion",
]


@dataclass
class DocumentExtractionManifest:
    """Canonical manifest for extraction provenance — per spec §5.4."""

    schema_version: str
    ingestion_id: str
    source_sha256: str
    detected_media_type: str
    converter: dict[str, str]
    markdown_sha256: str
    anchors: list[dict[str, Any]]
    warnings: list[str]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "schema_version": self.schema_version,
            "ingestion_id": self.ingestion_id,
            "source_sha256": self.source_sha256,
            "detected_media_type": self.detected_media_type,
            "converter": self.converter,
            "markdown_sha256": self.markdown_sha256,
            "anchors": self.anchors,
            "warnings": self.warnings,
            "generated_at": self.generated_at,
        }


@dataclass
class NormalizedKnowledgeCandidate:
    """Bundled normalized document and its extraction manifest."""

    knowledge_document: KnowledgeDocument
    manifest: dict[str, Any] | DocumentExtractionManifest


def normalize_conversion(
    result: ConversionResult,
    document: ValidatedDocument,
    ingestion_id: str,
) -> NormalizedKnowledgeCandidate:
    """Normalize conversion result into reviewable knowledge candidate.

    Đầu vào từ converter (Markdown, title, version, warnings) + preflight (object_key, SHA, MIME)
    → Markdown chuẩn hoá + chunks với anchor IDs + extraction manifest
    → KnowledgeDocument (status=review_pending, authority=USER_CONTENT) để lưu trữ.

    Args:
        result: ConversionResult from SafeMarkItDownConverter
        document: ValidatedDocument from preflight
        ingestion_id: Unique ingestion identifier for this upload

    Returns:
        NormalizedKnowledgeCandidate with KnowledgeDocument and manifest
    """

    # Extract workspace from object_key (format: quarantine/<workspace>/<ingestion_id>/original)
    parts = document.object_key.split("/")
    workspace_id = parts[1] if len(parts) >= 2 else "unknown"

    # Normalize markdown: clean encoding/line endings
    markdown = (result.markdown or "").strip()
    if markdown:
        # Normalize line endings to \n, handle UTF-8
        markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")

    # Parse headings and create anchor tree
    anchors, heading_tree = _parse_markdown_headings(markdown, document.detected_media_type)

    # Create deterministic chunks respecting heading boundaries
    chunks = _chunk_markdown_by_sections(
        markdown=markdown,
        heading_tree=heading_tree,
        workspace_id=workspace_id,
        ingestion_id=ingestion_id,
    )

    # Build KnowledgeDocument with review_pending status
    doc = KnowledgeDocument(
        workspace_id=workspace_id,
        title=result.title or "Untitled",
        source_uri=f"object://knowledge-ingestions/{ingestion_id}",
        media_type=result.package if result.package else document.detected_media_type,
        checksum=document.source_sha256,
        authority_class="USER_CONTENT",
        ingest_status="review_pending",
        chunks=chunks,
        metadata={
            "ingestion_id": ingestion_id,
            "source_sha256": document.source_sha256,
            "markdown_sha256": result.output_sha256 or _hash_markdown(markdown),
            "converter_name": result.package,
            "converter_version": result.version,
            "converter_profile": result.converter_profile,
            "manifest_schema_version": "cosa.document-extraction-manifest/v1",
            "scan_verdict": "clean",  # Preflight already passed scanner
            "warning_codes": result.warnings or [],
        },
    )

    # Build extraction manifest per spec §5.4
    manifest = DocumentExtractionManifest(
        schema_version="cosa.document-extraction-manifest/v1",
        ingestion_id=ingestion_id,
        source_sha256=document.source_sha256,
        detected_media_type=document.detected_media_type,
        converter={
            "name": result.package,
            "version": result.version,
            "profile": result.converter_profile,
        },
        markdown_sha256=result.output_sha256 or _hash_markdown(markdown),
        anchors=anchors,
        warnings=[str(w) for w in (result.warnings or [])],
        generated_at=datetime.now(UTC).isoformat(),
    )

    return NormalizedKnowledgeCandidate(
        knowledge_document=doc,
        manifest=manifest.to_dict(),
    )


def _hash_markdown(markdown: str) -> str:
    """Compute SHA-256 of markdown content."""
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def _parse_markdown_headings(
    markdown: str,
    media_type: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse Markdown headings and create anchor tree with stable IDs.

    Xây dựng mục lục từ headings (#, ##, ...) → anchor IDs (sec-001, sec-002, ...)
    Với media type XLSX/PPTX/DOCX, ưu tiên các tiêu đề loạt/sheet nếu có.

    Returns:
        (anchors list, heading_tree dict for chunking)
    """
    anchors: list[dict[str, Any]] = []
    heading_tree: dict[str, Any] = {}
    ordinal = 0

    if not markdown:
        return anchors, heading_tree

    # Split by heading lines (^# ... $)
    lines = markdown.split("\n")
    heading_stack: list[tuple[int, str, str]] = []  # (level, text, anchor_id)

    for line_idx, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if match:
            level = len(match.group(1))
            heading_text = match.group(2).strip()

            # Generate deterministic anchor ID based on ordinal
            ordinal += 1
            anchor_id = f"sec-{ordinal:03d}"

            # Record anchor
            anchors.append(
                {
                    "id": anchor_id,
                    "kind": "heading",
                    "label": heading_text,
                    "ordinal": ordinal,
                }
            )

            # Update heading stack (maintain hierarchy)
            heading_stack = [(lvl, t, aid) for lvl, t, aid in heading_stack if lvl < level]
            heading_stack.append((level, heading_text, anchor_id))

            # Track in tree for chunking
            if "headings" not in heading_tree:
                heading_tree["headings"] = []
            heading_tree["headings"].append(
                {
                    "level": level,
                    "text": heading_text,
                    "anchor_id": anchor_id,
                    "line_idx": line_idx,
                }
            )

    # If media type is XLSX/PPTX and headings look like sheet/slide labels, preserve them
    # (MarkItDown emits "## Sheet1", "## Sheet2" etc. for XLSX — these are already in headings)

    return anchors, heading_tree


def _chunk_markdown_by_sections(
    markdown: str,
    heading_tree: dict[str, Any],
    workspace_id: str,
    ingestion_id: str,
    chunk_size: int = 1024,
    overlap: int = 128,
) -> list[KnowledgeChunk]:
    """Chunk Markdown respecting heading boundaries.

    Phân chia Markdown thành chunks mà không cắt ngang heading, trừ khi
    một section tự dài vượt chunk_size — trong trường hợp đó ghi split_reason.

    Returns:
        List of KnowledgeChunk with anchor metadata
    """
    chunks: list[KnowledgeChunk] = []

    if not markdown:
        return chunks

    lines = markdown.split("\n")
    headings = heading_tree.get("headings", [])

    # Build section boundaries from headings
    section_ranges: list[tuple[str, int, int]] = []
    for i, heading_info in enumerate(headings):
        line_idx = heading_info["line_idx"]
        anchor_id = heading_info["anchor_id"]
        heading_text = heading_info["text"]

        # End of section is start of next section (or EOF)
        end_idx = headings[i + 1]["line_idx"] if i + 1 < len(headings) else len(lines)

        section_ranges.append((heading_text, line_idx, end_idx))

    # If no headings, treat entire content as one section
    if not section_ranges:
        section_ranges = [("Document", 0, len(lines))]

    # Chunk each section
    chunk_index = 0
    doc_id = f"doc_{ingestion_id[:12]}"

    for section_label, start_idx, end_idx in section_ranges:
        section_lines = lines[start_idx:end_idx]
        section_text = "\n".join(section_lines)

        if not section_text.strip():
            continue

        # Find anchor ID for this section
        anchor_id = None
        for heading_info in headings:
            if heading_info["line_idx"] == start_idx:
                anchor_id = heading_info["anchor_id"]
                break

        # If section is larger than chunk_size, split with reason
        if len(section_text.encode("utf-8")) > chunk_size:
            # Split within section
            sub_chunks = _split_long_text(
                section_text,
                chunk_size=chunk_size,
                overlap=overlap,
            )

            for sub_chunk_text in sub_chunks:
                chunk = KnowledgeChunk(
                    id=f"chk_{doc_id}_{chunk_index}",
                    document_id=doc_id,
                    workspace_id=workspace_id,
                    chunk_index=chunk_index,
                    content=sub_chunk_text,
                    chunker_name="document-section-v1",
                    chunker_version="1",
                    content_hash=hashlib.sha256(sub_chunk_text.encode("utf-8")).hexdigest(),
                    page_or_section=section_label,
                    metadata={
                        "anchor_id": anchor_id or "sec-000",
                        "split_reason": "section_too_large",
                    },
                )
                chunks.append(chunk)
                chunk_index += 1
        else:
            # Section fits in one chunk
            chunk = KnowledgeChunk(
                id=f"chk_{doc_id}_{chunk_index}",
                document_id=doc_id,
                workspace_id=workspace_id,
                chunk_index=chunk_index,
                content=section_text,
                chunker_name="document-section-v1",
                chunker_version="1",
                content_hash=hashlib.sha256(section_text.encode("utf-8")).hexdigest(),
                page_or_section=section_label,
                metadata={
                    "anchor_id": anchor_id or "sec-000",
                },
            )
            chunks.append(chunk)
            chunk_index += 1

    return chunks


def _split_long_text(
    text: str,
    chunk_size: int = 1024,
    overlap: int = 128,
) -> list[str]:
    """Split long text into overlapping chunks.

    Chia nhỏ text dài thành chunks có overlap để giữ ngữ cảnh.
    """
    chunks_list: list[str] = []
    text_bytes = text.encode("utf-8")

    if len(text_bytes) <= chunk_size:
        return [text]

    offset = 0
    while offset < len(text_bytes):
        chunk_end = min(offset + chunk_size, len(text_bytes))

        # Try to break at a boundary (newline)
        chunk_bytes = text_bytes[offset:chunk_end]
        try:
            chunk_text = chunk_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # If boundary is in the middle of a char, backtrack
            chunk_bytes = text_bytes[offset : chunk_end - 3]
            chunk_text = chunk_bytes.decode("utf-8", errors="ignore")

        chunks_list.append(chunk_text)

        # Move offset forward, accounting for overlap
        if offset + chunk_size >= len(text_bytes):
            break

        offset += chunk_size - overlap

    return chunks_list
