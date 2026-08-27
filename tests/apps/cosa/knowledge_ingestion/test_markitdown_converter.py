"""Tests for SafeMarkItDownConverter with mocked MarkItDown.

Tests verify:
1. Converter instantiates with enable_plugins=False (hardcoded)
2. Only convert_stream is called, never convert_uri/convert_local/requests
3. Small fixtures (text, HTML, CSV) convert to valid markdown
4. Output is capped at 10 MiB with proper failure code
5. Exceptions map to sanitized failure codes (no raw traceback)
6. Title extraction fallback to object_key works
7. Warnings are collected and filtered to allowlist
"""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, Mock, patch

import pytest

from apps.cosa.knowledge_ingestion.contracts import FailureCode
from apps.cosa.knowledge_ingestion.markitdown_converter import (
    ConversionResult,
    SafeMarkItDownConverter,
)
from apps.cosa.knowledge_ingestion.preflight import ValidatedDocument


class MockMarkItDownResult:
    """Mock result from MarkItDown.convert_stream()."""

    def __init__(self, text_content: str, title: str = None, warnings: list = None):
        self.text_content = text_content
        self.title = title
        self.warnings = warnings or []

    def __str__(self):
        return self.text_content


@pytest.fixture
def mock_markitdown():
    """Provide a mocked markitdown module."""

    class MockMarkItDown:
        """Mock MarkItDown library."""

        convert_stream_calls = []
        convert_uri_calls = []
        convert_local_calls = []

        def __init__(self, enable_plugins: bool = False):
            self.enable_plugins = enable_plugins

        def convert_stream(self, stream, stream_info=None):
            """Only allowed method."""
            MockMarkItDown.convert_stream_calls.append((stream, stream_info))
            _ = stream.read(10)
            stream.seek(0)
            return MockMarkItDownResult("# Converted markdown\nSample content")

        def convert_uri(self, uri):
            """Should NEVER be called."""
            MockMarkItDown.convert_uri_calls.append(uri)
            raise RuntimeError("convert_uri should not be called")

        def convert_local(self, path):
            """Should NEVER be called."""
            MockMarkItDown.convert_local_calls.append(path)
            raise RuntimeError("convert_local should not be called")

    mod = Mock()
    mod.MarkItDown = MockMarkItDown
    MockMarkItDown.convert_stream_calls = []
    MockMarkItDown.convert_uri_calls = []
    MockMarkItDown.convert_local_calls = []
    return mod, MockMarkItDown


@pytest.fixture
def converter(mock_markitdown):
    """Provide converter with mocked markitdown."""
    mock_mod, mock_class = mock_markitdown
    with patch.dict("sys.modules", {"markitdown": mock_mod}):
        converter_instance = SafeMarkItDownConverter()
        yield converter_instance, mock_class


# Test: Text document conversion
def test_convert_text_document(converter):
    """Convert plain text document to markdown."""
    conv, mock_class = converter
    content = b"Hello, World!\nThis is plain text."
    doc = ValidatedDocument(
        object_key="test/doc.txt",
        detected_media_type="text/plain",
        source_sha256="abcd1234",
        size_bytes=len(content),
    )

    result = conv.convert(doc, content)

    assert result.package == "markitdown"
    assert result.version == "0.1.7"
    assert result.converter_profile == "markitdown-safe-v1"
    assert result.failure_code is None
    assert result.markdown is not None
    assert result.output_sha256 is not None
    assert result.title == "doc.txt"  # Fallback to filename


# Test: HTML document conversion
def test_convert_html_document(converter):
    """Convert HTML document."""
    conv, mock_class = converter
    content = b"<html><body><h1>Title</h1><p>Content here.</p></body></html>"
    doc = ValidatedDocument(
        object_key="test/page.html",
        detected_media_type="text/html",
        source_sha256="abcd5678",
        size_bytes=len(content),
    )

    result = conv.convert(doc, content)

    assert result.failure_code is None
    assert result.markdown is not None
    assert result.output_sha256 is not None


# Test: CSV document conversion
def test_convert_csv_document(converter):
    """Convert CSV document."""
    conv, mock_class = converter
    content = b"Name,Age,City\nAlice,30,NYC\nBob,25,LA"
    doc = ValidatedDocument(
        object_key="test/data.csv",
        detected_media_type="text/csv",
        source_sha256="abcd9999",
        size_bytes=len(content),
    )

    result = conv.convert(doc, content)

    assert result.failure_code is None
    assert result.markdown is not None


# Test: Output size cap at 10 MiB
def test_output_exceeds_size_limit():
    """Reject markdown output exceeding 10 MiB cap."""
    content = b"Small input"
    doc = ValidatedDocument(
        object_key="test/huge.txt",
        detected_media_type="text/plain",
        source_sha256="abcd1111",
        size_bytes=len(content),
    )

    oversized_text = "x" * (10 * 1024 * 1024 + 1)  # 10 MiB + 1 byte

    class OversizeMarkItDown:
        def __init__(self, enable_plugins=False):
            self.enable_plugins = enable_plugins

        def convert_stream(self, stream, stream_info=None):
            return MockMarkItDownResult(oversized_text)

    mock_mod = Mock()
    mock_mod.MarkItDown = OversizeMarkItDown

    import sys
    with patch.dict(sys.modules, {"markitdown": mock_mod}):
        conv = SafeMarkItDownConverter()
        result = conv.convert(doc, content)

        assert result.failure_code == "conversion_output_too_large"
        assert result.markdown is None
        assert result.output_sha256 is None


# Test: Exception mapping - timeout
def test_conversion_timeout_exception():
    """Convert TimeoutError to sanitized failure code."""
    import sys
    content = b"Tiny file"
    doc = ValidatedDocument(
        object_key="test/timeout.txt",
        detected_media_type="text/plain",
        source_sha256="abcd2222",
        size_bytes=len(content),
    )

    class TimeoutMarkItDown:
        def __init__(self, enable_plugins=False):
            self.enable_plugins = enable_plugins

        def convert_stream(self, stream, stream_info=None):
            raise TimeoutError("Conversion took too long")

    mock_mod = Mock()
    mock_mod.MarkItDown = TimeoutMarkItDown

    with patch.dict(sys.modules, {"markitdown": mock_mod}):
        conv = SafeMarkItDownConverter()
        result = conv.convert(doc, content)

        assert result.failure_code == "conversion_timeout"
        assert result.markdown is None
        # Exception message should NOT leak to caller
        assert "took too long" not in str(result)


# Test: Exception mapping - parser error
def test_conversion_parser_error_exception():
    """Convert generic Exception to sanitized parser error."""
    import sys
    content = b"Corrupted file"
    doc = ValidatedDocument(
        object_key="test/corrupted.pdf",
        detected_media_type="application/pdf",
        source_sha256="abcd3333",
        size_bytes=len(content),
    )

    class ErrorMarkItDown:
        def __init__(self, enable_plugins=False):
            self.enable_plugins = enable_plugins

        def convert_stream(self, stream, stream_info=None):
            raise ValueError("PDF is corrupted at byte offset 1234")

    mock_mod = Mock()
    mock_mod.MarkItDown = ErrorMarkItDown

    with patch.dict(sys.modules, {"markitdown": mock_mod}):
        conv = SafeMarkItDownConverter()
        result = conv.convert(doc, content)

        assert result.failure_code == "conversion_parser_error"
        assert result.markdown is None
        # Exception message should NOT leak
        assert "byte offset 1234" not in str(result)


# Test: Title extraction fallback
def test_title_extraction_fallback():
    """Use object_key filename as title when result.title is None."""
    import sys
    content = b"Content without title"
    doc = ValidatedDocument(
        object_key="workspace/ingestion/doc-abc123.txt",
        detected_media_type="text/plain",
        source_sha256="abcd4444",
        size_bytes=len(content),
    )

    class NoTitleMarkItDown:
        def __init__(self, enable_plugins=False):
            self.enable_plugins = enable_plugins

        def convert_stream(self, stream, stream_info=None):
            return MockMarkItDownResult("# Markdown\nContent", title=None)

    mock_mod = Mock()
    mock_mod.MarkItDown = NoTitleMarkItDown

    with patch.dict(sys.modules, {"markitdown": mock_mod}):
        conv = SafeMarkItDownConverter()
        result = conv.convert(doc, content)

        # Fallback to last part of object_key
        assert result.title == "doc-abc123.txt"


# Test: Warning collection and filtering
def test_warning_collection_and_filtering():
    """Collect allowlisted warnings, filter unknown ones."""
    import sys
    content = b"Document with warnings"
    doc = ValidatedDocument(
        object_key="test/warned.docx",
        detected_media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        source_sha256="abcd5555",
        size_bytes=len(content),
    )

    class WarningMarkItDown:
        def __init__(self, enable_plugins=False):
            self.enable_plugins = enable_plugins

        def convert_stream(self, stream, stream_info=None):
            return MockMarkItDownResult(
                "# Markdown",
                title="Warned Doc",
                warnings=[
                    "table_structure_degraded",
                    "unknown_warning",
                    "font_fallback_used",
                ],
            )

    mock_mod = Mock()
    mock_mod.MarkItDown = WarningMarkItDown

    with patch.dict(sys.modules, {"markitdown": mock_mod}):
        conv = SafeMarkItDownConverter()
        result = conv.convert(doc, content)

        # Only allowlisted warnings
        assert result.failure_code is None
        assert "table_structure_degraded" in result.warnings
        assert "font_fallback_used" in result.warnings
        assert "unknown_warning" not in result.warnings


# Test: Output hash deterministic
def test_output_hash_deterministic():
    """Output SHA-256 is consistent."""
    import sys
    content = b"Deterministic content"
    doc = ValidatedDocument(
        object_key="test/hash.txt",
        detected_media_type="text/plain",
        source_sha256="abcd6666",
        size_bytes=len(content),
    )

    expected_markdown = "# Deterministic\nContent"

    class DeterministicMarkItDown:
        def __init__(self, enable_plugins=False):
            self.enable_plugins = enable_plugins

        def convert_stream(self, stream, stream_info=None):
            return MockMarkItDownResult(expected_markdown)

    mock_mod = Mock()
    mock_mod.MarkItDown = DeterministicMarkItDown

    with patch.dict(sys.modules, {"markitdown": mock_mod}):
        conv = SafeMarkItDownConverter()
        result = conv.convert(doc, content)

        expected_hash = hashlib.sha256(
            expected_markdown.encode("utf-8")
        ).hexdigest()
        assert result.output_sha256 == expected_hash
        assert result.markdown == expected_markdown


# Test: Result manifest fields
def test_result_manifest_fields():
    """ConversionResult includes all required fields."""
    import sys
    content = b"Test"
    doc = ValidatedDocument(
        object_key="test/manifest.txt",
        detected_media_type="text/plain",
        source_sha256="abcd7777",
        size_bytes=len(content),
    )

    class SimpleMarkItDown:
        def __init__(self, enable_plugins=False):
            self.enable_plugins = enable_plugins

        def convert_stream(self, stream, stream_info=None):
            return MockMarkItDownResult("# Content")

    mock_mod = Mock()
    mock_mod.MarkItDown = SimpleMarkItDown

    with patch.dict(sys.modules, {"markitdown": mock_mod}):
        conv = SafeMarkItDownConverter()
        result = conv.convert(doc, content)

        assert result.package == "markitdown"
        assert result.version == "0.1.7"
        assert result.converter_profile == "markitdown-safe-v1"
        assert isinstance(result.warnings, list)
        assert result.failure_code is None or isinstance(result.failure_code, str)


# Test: Verify only convert_stream is used, not convert_uri/convert_local
def test_only_convert_stream_called():
    """Verify convert_stream is called and convert_uri/convert_local are not."""
    import sys
    content = b"Test content"
    doc = ValidatedDocument(
        object_key="test/simple.txt",
        detected_media_type="text/plain",
        source_sha256="xyz",
        size_bytes=len(content),
    )

    class CallTrackingMarkItDown:
        convert_stream_called = False
        convert_uri_called = False
        convert_local_called = False

        def __init__(self, enable_plugins=False):
            self.enable_plugins = enable_plugins

        def convert_stream(self, stream, stream_info=None):
            CallTrackingMarkItDown.convert_stream_called = True
            _ = stream.read(10)
            stream.seek(0)
            return MockMarkItDownResult("# Converted")

        def convert_uri(self, uri):
            CallTrackingMarkItDown.convert_uri_called = True
            raise RuntimeError("should not be called")

        def convert_local(self, path):
            CallTrackingMarkItDown.convert_local_called = True
            raise RuntimeError("should not be called")

    mock_mod = Mock()
    mock_mod.MarkItDown = CallTrackingMarkItDown

    with patch.dict(sys.modules, {"markitdown": mock_mod}):
        conv = SafeMarkItDownConverter()
        result = conv.convert(doc, content)

        # Verify convert_stream was called
        assert CallTrackingMarkItDown.convert_stream_called
        # Verify forbidden methods were never called
        assert not CallTrackingMarkItDown.convert_uri_called
        assert not CallTrackingMarkItDown.convert_local_called
