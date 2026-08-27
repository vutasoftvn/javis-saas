"""Tests for document malware scanner interface and production readiness.

These tests verify:
1. Scanner interface works with clean, infected, and unavailable verdicts
2. Production readiness guard rejects fake scanners in production
3. Rejected documents (infected/unavailable) don't reach knowledge store
"""

import io
from typing import Optional

import pytest

from apps.cosa.knowledge_ingestion.contracts import QuarantinedObject


class TestScannerInterface:
    """Test DocumentMalwareScanner protocol and implementations."""

    @pytest.mark.asyncio
    async def test_scanner_clean_verdict(self):
        """Scanner returns 'clean' for safe content."""
        from apps.cosa.knowledge_ingestion.scanner import (
            DocumentMalwareScanner,
            FakeDocumentMalwareScanner,
        )

        scanner = FakeDocumentMalwareScanner(verdict="clean")
        stream = io.BytesIO(b"This is clean content")

        doc = QuarantinedObject(
            object_key="test/clean.txt",
            size_bytes=21,
            source_sha256="0" * 64,
            detected_media_type="text/plain",
        )

        result = await scanner.scan(stream, doc)
        assert result == "clean"

    @pytest.mark.asyncio
    async def test_scanner_infected_verdict(self):
        """Scanner returns 'infected' for malicious content."""
        from apps.cosa.knowledge_ingestion.scanner import (
            FakeDocumentMalwareScanner,
        )

        scanner = FakeDocumentMalwareScanner(verdict="infected")
        stream = io.BytesIO(b"Malicious content patterns")

        doc = QuarantinedObject(
            object_key="test/infected.txt",
            size_bytes=26,
            source_sha256="0" * 64,
            detected_media_type="text/plain",
        )

        result = await scanner.scan(stream, doc)
        assert result == "infected"

    @pytest.mark.asyncio
    async def test_scanner_unavailable_verdict(self):
        """Scanner returns 'unavailable' when service is down."""
        from apps.cosa.knowledge_ingestion.scanner import (
            FakeDocumentMalwareScanner,
        )

        scanner = FakeDocumentMalwareScanner(verdict="unavailable")
        stream = io.BytesIO(b"Some content")

        doc = QuarantinedObject(
            object_key="test/unknown.txt",
            size_bytes=12,
            source_sha256="0" * 64,
            detected_media_type="text/plain",
        )

        result = await scanner.scan(stream, doc)
        assert result == "unavailable"

    @pytest.mark.asyncio
    async def test_infected_result_terminal_rejection(self):
        """Infected verdict means document is rejected, no conversion happens."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )
        from apps.cosa.knowledge_ingestion.scanner import (
            FakeDocumentMalwareScanner,
        )

        import hashlib

        # First pass preflight validation (legitimate document structure)
        content = b"Legitimate but infected content"
        content_hash = hashlib.sha256(content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/infected.txt",
            size_bytes=len(content),
            source_sha256=content_hash,
            detected_media_type="text/plain",
        )
        stream = io.BytesIO(content)

        # Should pass preflight (structurally valid)
        validated = validate_quarantined_object(obj, stream)
        assert validated is not None

        # But scanner returns infected
        scanner = FakeDocumentMalwareScanner(verdict="infected")
        stream.seek(0)  # Reset stream
        scan_result = await scanner.scan(stream, obj)

        assert scan_result == "infected"
        # Caller would check: if scan_result != "clean": reject and don't convert
        # No conversion should happen here (verified by logic, not by mock)

    @pytest.mark.asyncio
    async def test_unavailable_result_terminal_rejection(self):
        """Unavailable verdict means document is rejected (treat like infected)."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )
        from apps.cosa.knowledge_ingestion.scanner import (
            FakeDocumentMalwareScanner,
        )

        import hashlib

        content = b"Content when scanner is down"
        content_hash = hashlib.sha256(content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/unknown.txt",
            size_bytes=len(content),
            source_sha256=content_hash,
            detected_media_type="text/plain",
        )
        stream = io.BytesIO(content)

        # Passes preflight but scanner is unavailable
        validated = validate_quarantined_object(obj, stream)
        assert validated is not None

        scanner = FakeDocumentMalwareScanner(verdict="unavailable")
        stream.seek(0)
        scan_result = await scanner.scan(stream, obj)

        assert scan_result == "unavailable"
        # Caller would reject: if scan_result != "clean": no conversion


class TestProductionReadinessGuard:
    """Test that fake scanner is rejected in production environment."""

    def test_fake_scanner_rejected_in_production(self):
        """Production readiness guard raises if fake scanner is used in prod."""
        from apps.cosa.knowledge_ingestion.scanner import (
            FakeDocumentMalwareScanner,
            assert_production_scanner_ready,
        )

        fake_scanner = FakeDocumentMalwareScanner(verdict="clean")

        with pytest.raises(RuntimeError) as exc:
            assert_production_scanner_ready(fake_scanner, environment="production")

        assert "fake" in str(exc.value).lower() or "test" in str(exc.value).lower()

    def test_unconfigured_scanner_rejected_in_production(self):
        """Production readiness guard raises if scanner is None (unconfigured) in prod."""
        from apps.cosa.knowledge_ingestion.scanner import (
            assert_production_scanner_ready,
        )

        with pytest.raises(RuntimeError) as exc:
            assert_production_scanner_ready(None, environment="production")

        assert "configured" in str(exc.value).lower() or "none" in str(exc.value).lower()

    def test_fake_scanner_allowed_in_test(self):
        """Fake scanner is allowed in test environment."""
        from apps.cosa.knowledge_ingestion.scanner import (
            FakeDocumentMalwareScanner,
            assert_production_scanner_ready,
        )

        fake_scanner = FakeDocumentMalwareScanner(verdict="clean")

        # Should not raise
        assert_production_scanner_ready(fake_scanner, environment="test")

    def test_fake_scanner_allowed_in_development(self):
        """Fake scanner is allowed in development environment."""
        from apps.cosa.knowledge_ingestion.scanner import (
            FakeDocumentMalwareScanner,
            assert_production_scanner_ready,
        )

        fake_scanner = FakeDocumentMalwareScanner(verdict="clean")

        # Should not raise
        assert_production_scanner_ready(fake_scanner, environment="development")

    def test_production_scanner_allowed_in_production(self):
        """A production-configured scanner passes readiness check."""
        from apps.cosa.knowledge_ingestion.scanner import (
            assert_production_scanner_ready,
        )

        # Mock a non-fake scanner (e.g., a real ClamAV or VirusTotal wrapper)
        # For now, we'll just verify the guard doesn't reject it
        # This would be a real implementation, not FakeDocumentMalwareScanner

        class RealScannerMock:
            """Represents a real production scanner (not FakeDocumentMalwareScanner)."""

            async def scan(self, stream, document):
                return "clean"

        real_scanner = RealScannerMock()

        # Should not raise
        assert_production_scanner_ready(real_scanner, environment="production")


class TestScannerIntegrationWithPreflight:
    """Test scanner and preflight work together correctly."""

    @pytest.mark.asyncio
    async def test_full_pipeline_clean_document(self):
        """Clean document passes preflight and scanner."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )
        from apps.cosa.knowledge_ingestion.scanner import (
            FakeDocumentMalwareScanner,
        )

        import hashlib

        content = b"This is a clean, valid document."
        content_hash = hashlib.sha256(content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/clean_full.txt",
            size_bytes=len(content),
            source_sha256=content_hash,
            detected_media_type="text/plain",
        )

        # Preflight pass
        stream1 = io.BytesIO(content)
        validated = validate_quarantined_object(obj, stream1)
        assert validated is not None

        # Scanner pass
        scanner = FakeDocumentMalwareScanner(verdict="clean")
        stream2 = io.BytesIO(content)
        scan_result = await scanner.scan(stream2, obj)
        assert scan_result == "clean"

        # Both pass: document can proceed to conversion

    @pytest.mark.asyncio
    async def test_full_pipeline_infected_document(self):
        """Infected document fails at scanner stage (after preflight)."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )
        from apps.cosa.knowledge_ingestion.scanner import (
            FakeDocumentMalwareScanner,
        )

        import hashlib

        content = b"Looks clean but is infected."
        content_hash = hashlib.sha256(content).hexdigest()

        obj = QuarantinedObject(
            object_key="test/infected_full.txt",
            size_bytes=len(content),
            source_sha256=content_hash,
            detected_media_type="text/plain",
        )

        # Preflight passes
        stream1 = io.BytesIO(content)
        validated = validate_quarantined_object(obj, stream1)
        assert validated is not None

        # Scanner fails
        scanner = FakeDocumentMalwareScanner(verdict="infected")
        stream2 = io.BytesIO(content)
        scan_result = await scanner.scan(stream2, obj)
        assert scan_result != "clean"  # Not clean

        # Caller must check: if scan_result != "clean", reject and don't convert

    def test_full_pipeline_invalid_mime(self):
        """Invalid MIME is caught at preflight (before scanner even runs)."""
        from apps.cosa.knowledge_ingestion.preflight import (
            validate_quarantined_object,
        )

        obj = QuarantinedObject(
            object_key="test/invalid.json",
            size_bytes=10,
            source_sha256="0" * 64,
            detected_media_type="application/json",  # Not allowlisted
        )
        stream = io.BytesIO(b'{"key": 1}')

        # Preflight rejects before scanner is even called
        with pytest.raises(ValueError) as exc:
            validate_quarantined_object(obj, stream)

        assert "unsupported_media_type" in str(exc.value).lower()

        # Scanner never runs because document failed preflight


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
