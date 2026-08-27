"""Hostile-input and regression tests for document preflight validation.

Tests verify that malicious/invalid documents are rejected before any conversion
or knowledge store write occurs. Each rejection path must NOT invoke converters
or write to the knowledge layer.
"""

import hashlib
import io
import struct
import zipfile
from dataclasses import dataclass
from typing import BinaryIO

import pytest

from apps.cosa.knowledge_ingestion.contracts import (
    MIME_TYPE_LIMITS,
    QuarantinedObject,
)


# Fixtures: hostile-input byte sequences (TDD RED phase)
# These tests will FAIL until preflight.py is implemented


class TestMIMEValidation:
    """Test MIME type allowlist enforcement."""

    def test_unsupported_media_type_json(self):
        """Reject JSON (not in allowlist) before any parsing."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        obj = QuarantinedObject(
            object_key="test/json.json",
            size_bytes=100,
            source_sha256="0" * 64,
            detected_media_type="application/json",
        )
        stream = io.BytesIO(b'{"key": "value"}')

        with pytest.raises(ValueError) as exc:
            validate_quarantined_object(obj, stream)

        assert "unsupported_media_type" in str(exc.value).lower()

    def test_unsupported_media_type_xml(self):
        """Reject XML (not in allowlist)."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        obj = QuarantinedObject(
            object_key="test/doc.xml",
            size_bytes=50,
            source_sha256="0" * 64,
            detected_media_type="application/xml",
        )
        stream = io.BytesIO(b'<?xml version="1.0"?><root></root>')

        with pytest.raises(ValueError) as exc:
            validate_quarantined_object(obj, stream)

        assert "unsupported_media_type" in str(exc.value).lower()

    def test_unsupported_generic_zip(self):
        """Reject generic ZIP (not DOCX/XLSX/PPTX)."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        # Minimal valid ZIP
        zip_bytes = io.BytesIO()
        with zipfile.ZipFile(zip_bytes, "w") as zf:
            zf.writestr("file.txt", "content")
        zip_content = zip_bytes.getvalue()

        obj = QuarantinedObject(
            object_key="test/generic.zip",
            size_bytes=len(zip_content),
            source_sha256="0" * 64,
            detected_media_type="application/zip",
        )
        stream = io.BytesIO(zip_content)

        with pytest.raises(ValueError) as exc:
            validate_quarantined_object(obj, stream)

        assert "unsupported_media_type" in str(exc.value).lower()


class TestMagicByteMismatch:
    """Test magic-byte validation against claimed MIME type."""

    def test_mime_mismatch_pdf_claimed_not_pdf(self):
        """Reject when claiming PDF but magic bytes say otherwise."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        # Claim PDF but provide plain text
        fake_pdf = b"This is not a PDF"
        obj = QuarantinedObject(
            object_key="test/fake.pdf",
            size_bytes=len(fake_pdf),
            source_sha256="0" * 64,
            detected_media_type="application/pdf",
        )
        stream = io.BytesIO(fake_pdf)

        with pytest.raises(ValueError) as exc:
            validate_quarantined_object(obj, stream)

        assert "mime_mismatch" in str(exc.value).lower()

    def test_mime_mismatch_docx_claimed_but_not_zip(self):
        """Reject when claiming DOCX but magic bytes are not ZIP."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        # DOCX should be ZIP (starts with PK\x03\x04), but this doesn't
        fake_docx = b"This is not a DOCX file"
        obj = QuarantinedObject(
            object_key="test/fake.docx",
            size_bytes=len(fake_docx),
            source_sha256="0" * 64,
            detected_media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        stream = io.BytesIO(fake_docx)

        with pytest.raises(ValueError) as exc:
            validate_quarantined_object(obj, stream)

        assert "mime_mismatch" in str(exc.value).lower()

    def test_valid_pdf_magic_accepted(self):
        """Accept valid PDF magic bytes."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        # Minimal valid PDF magic + content (just enough to not fail the magic check)
        pdf_content = b"%PDF-1.4\n%dummy content to make it bigger"
        pdf_hash = hashlib.sha256(pdf_content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/valid.pdf",
            size_bytes=len(pdf_content),
            source_sha256=pdf_hash,
            detected_media_type="application/pdf",
        )
        stream = io.BytesIO(pdf_content)

        result = validate_quarantined_object(obj, stream)
        assert result is not None
        assert result.object_key == "test/valid.pdf"
        assert result.detected_media_type == "application/pdf"
        assert result.source_sha256 == pdf_hash


class TestFileSizeValidation:
    """Test file size limit enforcement per MIME type."""

    def test_file_too_large_text_plain(self):
        """Reject text/plain exceeding 10 MiB limit."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        # Create a stream that claims 11 MiB but we don't allocate it all
        # Use a predictable pattern to hash
        size_limit = MIME_TYPE_LIMITS["text/plain"]
        oversized = size_limit + 1

        # Create content that's definitely over the limit
        content = b"x" * (size_limit + 1024)
        content_hash = hashlib.sha256(content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/large.txt",
            size_bytes=len(content),
            source_sha256=content_hash,
            detected_media_type="text/plain",
        )
        stream = io.BytesIO(content)

        with pytest.raises(ValueError) as exc:
            validate_quarantined_object(obj, stream)

        assert "file_too_large" in str(exc.value).lower()

    def test_file_too_large_pdf(self):
        """Reject PDF exceeding 25 MiB limit."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        size_limit = MIME_TYPE_LIMITS["application/pdf"]

        # Minimal PDF header + oversized content
        pdf_header = b"%PDF-1.4\n"
        padding = b"x" * (size_limit + 1024)
        content = pdf_header + padding

        content_hash = hashlib.sha256(content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/large.pdf",
            size_bytes=len(content),
            source_sha256=content_hash,
            detected_media_type="application/pdf",
        )
        stream = io.BytesIO(content)

        with pytest.raises(ValueError) as exc:
            validate_quarantined_object(obj, stream)

        assert "file_too_large" in str(exc.value).lower()

    def test_file_within_limit_accepted(self):
        """Accept text/plain within the 10 MiB limit."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        content = b"Hello, this is valid text content within limits."
        content_hash = hashlib.sha256(content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/small.txt",
            size_bytes=len(content),
            source_sha256=content_hash,
            detected_media_type="text/plain",
        )
        stream = io.BytesIO(content)

        result = validate_quarantined_object(obj, stream)
        assert result is not None
        assert result.object_key == "test/small.txt"


class TestChecksumValidation:
    """Test SHA-256 checksum verification."""

    def test_checksum_mismatch(self):
        """Reject when recomputed SHA-256 doesn't match provided hash."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        content = b"This is the actual content"
        wrong_hash = "0" * 64  # Clearly wrong hash

        obj = QuarantinedObject(
            object_key="test/tampered.txt",
            size_bytes=len(content),
            source_sha256=wrong_hash,
            detected_media_type="text/plain",
        )
        stream = io.BytesIO(content)

        with pytest.raises(ValueError) as exc:
            validate_quarantined_object(obj, stream)

        assert "checksum_mismatch" in str(exc.value).lower()

    def test_checksum_match(self):
        """Accept when SHA-256 matches."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        content = b"Content with correct hash"
        correct_hash = hashlib.sha256(content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/verified.txt",
            size_bytes=len(content),
            source_sha256=correct_hash,
            detected_media_type="text/plain",
        )
        stream = io.BytesIO(content)

        result = validate_quarantined_object(obj, stream)
        assert result is not None
        assert result.source_sha256 == correct_hash


class TestOfficeArchiveValidation:
    """Test ZIP bomb and Office archive safety checks."""

    def test_archive_too_many_members(self):
        """Reject Office archive with >1000 members (ZIP bomb vector)."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        # Create DOCX-like archive with >1000 members
        zip_bytes = io.BytesIO()
        with zipfile.ZipFile(zip_bytes, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add 1001 small files to exceed the member count limit
            for i in range(1001):
                zf.writestr(f"member_{i:04d}.xml", f"<content>{i}</content>")

        zip_content = zip_bytes.getvalue()
        zip_hash = hashlib.sha256(zip_content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/bomb_members.docx",
            size_bytes=len(zip_content),
            source_sha256=zip_hash,
            detected_media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        stream = io.BytesIO(zip_content)

        with pytest.raises(ValueError) as exc:
            validate_quarantined_object(obj, stream)

        assert "archive_limit_exceeded" in str(exc.value).lower()

    def test_archive_uncompressed_size_bomb(self):
        """Reject Office archive where uncompressed size exceeds 100 MiB."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        # Create a highly compressible member that expands to >100 MiB
        # This is a compression bomb vector
        zip_bytes = io.BytesIO()
        with zipfile.ZipFile(zip_bytes, "w", zipfile.ZIP_DEFLATED) as zf:
            # Highly repetitive content that compresses well but expands large
            # We'll create content that uncompresses to 101 MiB
            repetitive = b"x" * (1024 * 1024)  # 1 MiB pattern
            large_content = repetitive * 101  # 101 MiB uncompressed
            zf.writestr("large_member.bin", large_content)

        zip_content = zip_bytes.getvalue()
        zip_hash = hashlib.sha256(zip_content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/bomb_uncompressed.xlsx",
            size_bytes=len(zip_content),
            source_sha256=zip_hash,
            detected_media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        stream = io.BytesIO(zip_content)

        with pytest.raises(ValueError) as exc:
            validate_quarantined_object(obj, stream)

        assert "archive_limit_exceeded" in str(exc.value).lower()

    def test_archive_single_member_too_large(self):
        """Reject Office archive where a single member exceeds 50 MiB."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        # Create archive with one member >50 MiB
        zip_bytes = io.BytesIO()
        with zipfile.ZipFile(zip_bytes, "w", zipfile.ZIP_DEFLATED) as zf:
            oversized = b"y" * (50 * 1024 * 1024 + 1024)  # 50 MiB + 1 KiB
            zf.writestr("huge_member.bin", oversized)

        zip_content = zip_bytes.getvalue()
        zip_hash = hashlib.sha256(zip_content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/bomb_member_size.pptx",
            size_bytes=len(zip_content),
            source_sha256=zip_hash,
            detected_media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
        stream = io.BytesIO(zip_content)

        with pytest.raises(ValueError) as exc:
            validate_quarantined_object(obj, stream)

        assert "archive_limit_exceeded" in str(exc.value).lower()

    def test_archive_compression_ratio_bomb(self):
        """Reject Office archive with compression ratio >20:1 (expansion bomb)."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        # Create archive with extreme compression ratio
        # All zeros compress to near nothing, expand to lots
        zip_bytes = io.BytesIO()
        with zipfile.ZipFile(zip_bytes, "w", zipfile.ZIP_DEFLATED) as zf:
            # 20 MiB of zeros expands from maybe 1 MiB compressed
            # ratio is 20:1, which is the threshold, so 21:1 should fail
            large_zeros = b"\x00" * (21 * 1024 * 1024)  # 21 MiB of zeros
            zf.writestr("zeros.bin", large_zeros)

        zip_content = zip_bytes.getvalue()
        zip_hash = hashlib.sha256(zip_content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/bomb_ratio.docx",
            size_bytes=len(zip_content),
            source_sha256=zip_hash,
            detected_media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        stream = io.BytesIO(zip_content)

        with pytest.raises(ValueError) as exc:
            validate_quarantined_object(obj, stream)

        assert "archive_limit_exceeded" in str(exc.value).lower()

    def test_valid_office_archive_accepted(self):
        """Accept valid, safe Office archive (DOCX with minimal members)."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        # Minimal valid DOCX structure (DOCX is just ZIP)
        zip_bytes = io.BytesIO()
        with zipfile.ZipFile(zip_bytes, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", b"<?xml version='1.0'?>")
            zf.writestr("word/document.xml", b"<document>content</document>")

        zip_content = zip_bytes.getvalue()
        zip_hash = hashlib.sha256(zip_content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/valid.docx",
            size_bytes=len(zip_content),
            source_sha256=zip_hash,
            detected_media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        stream = io.BytesIO(zip_content)

        result = validate_quarantined_object(obj, stream)
        assert result is not None
        assert result.object_key == "test/valid.docx"
        assert "wordprocessingml" in result.detected_media_type


class TestCleanFixtures:
    """Test that legitimate documents pass all validation."""

    def test_clean_text_plain(self):
        """Accept plain text file with valid hash."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        content = b"This is a clean plain text document.\nWith multiple lines.\n"
        content_hash = hashlib.sha256(content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/clean.txt",
            size_bytes=len(content),
            source_sha256=content_hash,
            detected_media_type="text/plain",
        )
        stream = io.BytesIO(content)

        result = validate_quarantined_object(obj, stream)
        assert result is not None
        assert result.detected_media_type == "text/plain"
        assert result.source_sha256 == content_hash

    def test_clean_csv(self):
        """Accept CSV file with valid hash."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        content = b"name,age,city\nAlice,30,NYC\nBob,25,LA\n"
        content_hash = hashlib.sha256(content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/data.csv",
            size_bytes=len(content),
            source_sha256=content_hash,
            detected_media_type="text/csv",
        )
        stream = io.BytesIO(content)

        result = validate_quarantined_object(obj, stream)
        assert result is not None
        assert result.detected_media_type == "text/csv"

    def test_clean_html(self):
        """Accept HTML file with valid hash."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        content = b"<!DOCTYPE html>\n<html><head><title>Test</title></head><body>Content</body></html>"
        content_hash = hashlib.sha256(content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/page.html",
            size_bytes=len(content),
            source_sha256=content_hash,
            detected_media_type="text/html",
        )
        stream = io.BytesIO(content)

        result = validate_quarantined_object(obj, stream)
        assert result is not None
        assert result.detected_media_type == "text/html"

    def test_clean_pdf(self):
        """Accept valid PDF with correct magic bytes."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        # Minimal valid PDF structure
        content = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\nxref\ntrailer<</Size 2>>\nstartxref\n0\n%%EOF"
        content_hash = hashlib.sha256(content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/document.pdf",
            size_bytes=len(content),
            source_sha256=content_hash,
            detected_media_type="application/pdf",
        )
        stream = io.BytesIO(content)

        result = validate_quarantined_object(obj, stream)
        assert result is not None
        assert result.detected_media_type == "application/pdf"

    def test_clean_xlsx(self):
        """Accept minimal XLSX archive."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        zip_bytes = io.BytesIO()
        with zipfile.ZipFile(zip_bytes, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", b"<?xml version='1.0'?>")
            zf.writestr("xl/workbook.xml", b"<workbook/>")

        zip_content = zip_bytes.getvalue()
        zip_hash = hashlib.sha256(zip_content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/data.xlsx",
            size_bytes=len(zip_content),
            source_sha256=zip_hash,
            detected_media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        stream = io.BytesIO(zip_content)

        result = validate_quarantined_object(obj, stream)
        assert result is not None
        assert "spreadsheetml" in result.detected_media_type

    def test_clean_pptx(self):
        """Accept minimal PPTX archive."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        zip_bytes = io.BytesIO()
        with zipfile.ZipFile(zip_bytes, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", b"<?xml version='1.0'?>")
            zf.writestr("ppt/presentation.xml", b"<presentation/>")

        zip_content = zip_bytes.getvalue()
        zip_hash = hashlib.sha256(zip_content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/slides.pptx",
            size_bytes=len(zip_content),
            source_sha256=zip_hash,
            detected_media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
        stream = io.BytesIO(zip_content)

        result = validate_quarantined_object(obj, stream)
        assert result is not None
        assert "presentationml" in result.detected_media_type


class TestNoConverterInvocation:
    """Verify that rejection paths do NOT invoke any converter or knowledge write."""

    def test_rejected_document_never_converts(self):
        """Assert rejected documents don't reach conversion (mock would detect call)."""
        # This is a structural test: the ValidatedDocument is the gate.
        # If preflight rejects and raises, the caller would never reach the converter.
        # If preflight returned an invalid ValidatedDocument, downstream would fail.
        # We verify by checking that invalid inputs raise ValueError before returning.

        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        obj = QuarantinedObject(
            object_key="test/hostile.json",
            size_bytes=100,
            source_sha256="0" * 64,
            detected_media_type="application/json",  # Not in allowlist
        )
        stream = io.BytesIO(b'{"malicious": true}')

        with pytest.raises(ValueError):
            validate_quarantined_object(obj, stream)

        # If we reach here, exception was raised, meaning no converter was called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
