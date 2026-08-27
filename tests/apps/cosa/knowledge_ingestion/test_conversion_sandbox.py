"""Tests for DocumentConversionSandbox abstraction and readiness guard.

Tests verify:
1. InProcessConversionSandbox is marked as test-only
2. async run() delegates to SafeMarkItDownConverter
3. Production readiness guard:
   - Passes in non-production environment
   - Rejects test-only sandbox in production
   - Rejects missing resource/egress attestation in production
4. Sandbox protocol is properly defined
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from apps.cosa.knowledge_ingestion.conversion_sandbox import (
    DocumentConversionSandbox,
    InProcessConversionSandbox,
    assert_production_conversion_ready,
)
from apps.cosa.knowledge_ingestion.markitdown_converter import ConversionResult
from apps.cosa.knowledge_ingestion.preflight import ValidatedDocument
from apps.cosa.knowledge_ingestion.scanner import FakeDocumentMalwareScanner


class MockConversionSandbox:
    """Mock sandbox that implements the protocol."""

    async def run(self, document, content, converter_profile):
        """Mock implementation."""
        return ConversionResult(
            markdown="# Mock",
            title="Mock",
            package="mock",
            version="1.0",
            converter_profile=converter_profile,
            output_sha256="abc123",
            warnings=[],
            failure_code=None,
        )


@pytest.fixture
def valid_document():
    """Provide a valid test document."""
    return ValidatedDocument(
        object_key="test/document.txt",
        detected_media_type="text/plain",
        source_sha256="test_sha256",
        size_bytes=100,
    )


@pytest.fixture
def test_content():
    """Provide test document bytes."""
    return b"Test document content"


# Test: InProcessConversionSandbox delegation
@pytest.mark.asyncio
async def test_inprocess_sandbox_delegates_to_converter(valid_document, test_content):
    """InProcessConversionSandbox delegates to SafeMarkItDownConverter."""
    import sys
    mock_mod = Mock()
    mock_mod.MarkItDown = Mock(return_value=Mock(convert_stream=Mock()))

    with patch.dict(sys.modules, {"markitdown": mock_mod}):
        with patch(
            "apps.cosa.knowledge_ingestion.conversion_sandbox.SafeMarkItDownConverter"
        ) as mock_converter_class:
            mock_converter = Mock()
            mock_converter.convert.return_value = ConversionResult(
                markdown="# Converted",
                title="Test",
                package="markitdown",
                version="0.1.7",
                converter_profile="markitdown-safe-v1",
                output_sha256="hash123",
                warnings=[],
                failure_code=None,
            )
            mock_converter_class.return_value = mock_converter

            sandbox = InProcessConversionSandbox()
            result = await sandbox.run(
                valid_document, test_content, "markitdown-safe-v1"
            )

            # Verify converter was called
            mock_converter.convert.assert_called_once_with(valid_document, test_content)
            assert result.markdown == "# Converted"


# Test: InProcessConversionSandbox rejects unknown profiles
@pytest.mark.asyncio
async def test_inprocess_sandbox_rejects_unknown_profile(
    valid_document, test_content
):
    """InProcessConversionSandbox returns error for unknown converter_profile."""
    import sys
    mock_mod = Mock()
    mock_mod.MarkItDown = Mock(return_value=Mock(convert_stream=Mock()))

    with patch.dict(sys.modules, {"markitdown": mock_mod}):
        with patch(
            "apps.cosa.knowledge_ingestion.conversion_sandbox.SafeMarkItDownConverter"
        ):
            sandbox = InProcessConversionSandbox()
            result = await sandbox.run(
                valid_document, test_content, "unknown-profile"
            )

            assert result.failure_code == "conversion_parser_error"
            assert result.markdown is None


# Test: Production readiness in non-production environment
def test_production_ready_non_production():
    """Readiness check passes in non-production environment."""
    import sys
    mock_mod = Mock()
    mock_mod.MarkItDown = Mock(return_value=Mock(convert_stream=Mock()))

    with patch.dict(sys.modules, {"markitdown": mock_mod}):
        sandbox = InProcessConversionSandbox()

        # Should not raise in development
        assert_production_conversion_ready(
            sandbox, scanner=FakeDocumentMalwareScanner("clean"), environment="development"
        )


def test_production_ready_staging():
    """Readiness check passes in staging environment."""
    import sys
    mock_mod = Mock()
    mock_mod.MarkItDown = Mock(return_value=Mock(convert_stream=Mock()))

    with patch.dict(sys.modules, {"markitdown": mock_mod}):
        sandbox = InProcessConversionSandbox()

        # Should not raise in staging
        assert_production_conversion_ready(
            sandbox, scanner=FakeDocumentMalwareScanner("clean"), environment="staging"
        )


# Test: Production readiness rejects test-only sandbox
def test_production_ready_rejects_inprocess_sandbox():
    """Readiness check fails in production with test-only sandbox."""
    import sys
    mock_mod = Mock()
    mock_mod.MarkItDown = Mock(return_value=Mock(convert_stream=Mock()))

    with patch.dict(sys.modules, {"markitdown": mock_mod}):
        sandbox = InProcessConversionSandbox()

        with pytest.raises(RuntimeError) as exc_info:
            assert_production_conversion_ready(
                sandbox, scanner=FakeDocumentMalwareScanner("clean"), environment="production"
            )

        assert "InProcessConversionSandbox is test-only" in str(exc_info.value)


# Test: Production readiness rejects None sandbox in production
def test_production_ready_rejects_none_sandbox():
    """Readiness check fails in production with None sandbox."""
    with pytest.raises(RuntimeError) as exc_info:
        assert_production_conversion_ready(
            None, scanner=FakeDocumentMalwareScanner("clean"), environment="production"
        )

    assert "sandbox is None" in str(exc_info.value)


# Test: Production readiness rejects None scanner (via composed guard)
def test_production_ready_rejects_failed_scanner():
    """Readiness check fails in production if scanner is None (via composed guard)."""
    mock_sandbox = Mock(spec=DocumentConversionSandbox)

    with pytest.raises(RuntimeError) as exc_info:
        assert_production_conversion_ready(
            mock_sandbox, scanner=None, environment="production"
        )

    # Error message comes from composed assert_production_scanner_ready
    assert "malware scanner" in str(exc_info.value).lower()


# Test: Production readiness requires resource limits attestation
def test_production_ready_requires_resource_limits_attestation():
    """Readiness check fails without resource limits attestation."""
    mock_sandbox = Mock(spec=DocumentConversionSandbox)
    # Mock a real scanner (not FakeDocumentMalwareScanner) to pass scanner check
    from apps.cosa.knowledge_ingestion.scanner import DocumentMalwareScanner
    mock_scanner = Mock(spec=DocumentMalwareScanner)

    # Clear the env var to ensure it's not set
    with patch.dict(
        os.environ,
        {"KNOWLEDGE_INGESTION_RESOURCE_LIMITS_ATTESTED": "false"},
        clear=False,
    ):
        with pytest.raises(RuntimeError) as exc_info:
            assert_production_conversion_ready(
                mock_sandbox,
                scanner=mock_scanner,
                environment="production",
            )

        assert "KNOWLEDGE_INGESTION_RESOURCE_LIMITS_ATTESTED" in str(
            exc_info.value
        )


# Test: Production readiness requires egress-deny attestation
def test_production_ready_requires_egress_deny_attestation():
    """Readiness check fails without egress-deny attestation."""
    mock_sandbox = Mock(spec=DocumentConversionSandbox)
    # Mock a real scanner to pass scanner check
    from apps.cosa.knowledge_ingestion.scanner import DocumentMalwareScanner
    mock_scanner = Mock(spec=DocumentMalwareScanner)

    # Set resource limits but not egress-deny
    with patch.dict(
        os.environ,
        {
            "KNOWLEDGE_INGESTION_RESOURCE_LIMITS_ATTESTED": "true",
            "KNOWLEDGE_INGESTION_EGRESS_DENY_ATTESTED": "false",
        },
        clear=False,
    ):
        with pytest.raises(RuntimeError) as exc_info:
            assert_production_conversion_ready(
                mock_sandbox,
                scanner=mock_scanner,
                environment="production",
            )

        assert "KNOWLEDGE_INGESTION_EGRESS_DENY_ATTESTED" in str(
            exc_info.value
        )


# Test: Production readiness passes with all attestations
def test_production_ready_accepts_full_attestation():
    """Readiness check passes when all attestations are present."""
    mock_sandbox = Mock(spec=DocumentConversionSandbox)
    # Mock a real scanner to pass scanner check
    from apps.cosa.knowledge_ingestion.scanner import DocumentMalwareScanner
    mock_scanner = Mock(spec=DocumentMalwareScanner)

    with patch.dict(
        os.environ,
        {
            "KNOWLEDGE_INGESTION_RESOURCE_LIMITS_ATTESTED": "true",
            "KNOWLEDGE_INGESTION_EGRESS_DENY_ATTESTED": "true",
        },
        clear=False,
    ):
        # Should not raise
        assert_production_conversion_ready(
            mock_sandbox,
            scanner=mock_scanner,
            environment="production",
        )


# Test: Production readiness accepts alternate true values
def test_production_ready_accepts_alternate_true_values():
    """Readiness check accepts '1', 'yes', 'YES' as true."""
    mock_sandbox = Mock(spec=DocumentConversionSandbox)
    # Mock a real scanner to pass scanner check
    from apps.cosa.knowledge_ingestion.scanner import DocumentMalwareScanner
    mock_scanner = Mock(spec=DocumentMalwareScanner)

    for true_value in ["1", "yes", "YES"]:
        with patch.dict(
            os.environ,
            {
                "KNOWLEDGE_INGESTION_RESOURCE_LIMITS_ATTESTED": true_value,
                "KNOWLEDGE_INGESTION_EGRESS_DENY_ATTESTED": true_value,
            },
            clear=False,
        ):
            # Should not raise
            assert_production_conversion_ready(
                mock_sandbox,
                scanner=mock_scanner,
                environment="production",
            )


# Test: Protocol is runtime-checkable
def test_sandbox_protocol_is_runtime_checkable():
    """DocumentConversionSandbox protocol can be checked at runtime."""
    mock_sandbox = Mock()
    mock_sandbox.run = Mock()

    # Mock should be compatible with protocol
    assert isinstance(mock_sandbox, DocumentConversionSandbox)


# Test: Inprocess sandbox implements protocol
def test_inprocess_sandbox_implements_protocol():
    """InProcessConversionSandbox implements DocumentConversionSandbox protocol."""
    import sys
    mock_mod = Mock()
    mock_mod.MarkItDown = Mock(return_value=Mock(convert_stream=Mock()))

    with patch.dict(sys.modules, {"markitdown": mock_mod}):
        sandbox = InProcessConversionSandbox()
        assert isinstance(sandbox, DocumentConversionSandbox)


# Test: Mock sandbox in tests
class MockSandboxImpl:
    """Mock sandbox for use in tests."""

    def __init__(self):
        self.calls = []

    async def run(self, document, content, converter_profile):
        """Track calls."""
        self.calls.append(
            {
                "document": document,
                "content": content,
                "converter_profile": converter_profile,
            }
        )
        return ConversionResult(
            markdown="# Mock result",
            title="Mock",
            package="mock",
            version="1.0",
            converter_profile=converter_profile,
            output_sha256="mock_hash",
            warnings=[],
            failure_code=None,
        )


@pytest.mark.asyncio
async def test_mock_sandbox_works():
    """Verify mock sandbox implementation works."""
    sandbox = MockSandboxImpl()
    doc = ValidatedDocument(
        object_key="test/doc.txt",
        detected_media_type="text/plain",
        source_sha256="test",
        size_bytes=10,
    )
    content = b"test"

    result = await sandbox.run(doc, content, "test-profile")

    assert result.markdown == "# Mock result"
    assert len(sandbox.calls) == 1
    assert sandbox.calls[0]["document"] == doc
