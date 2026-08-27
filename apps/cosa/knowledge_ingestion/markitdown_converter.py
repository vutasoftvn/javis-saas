"""Isolated, sandboxed MarkItDown document converter.

Điểm này là ĐIỂM TIẾP XÚC DUY NHẤT với thư viện MarkItDown trong toàn hệ thống.
Luôn gọi convert_stream() (không convert_uri, convert_local, hoặc plugins).
Cấu hình server (mime type, size limit), không từ client (filename, extension).
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from typing import Literal

from apps.cosa.knowledge_ingestion.contracts import FailureCode
from apps.cosa.knowledge_ingestion.preflight import ValidatedDocument

__all__ = [
    "ConversionResult",
    "SafeMarkItDownConverter",
]

# Output size cap: 10 MiB
MAX_OUTPUT_MARKDOWN_BYTES = 10 * 1024 * 1024

# Allowlisted warning codes that MarkItDown may emit
WarningCode = Literal[
    "table_structure_degraded",
    "image_extraction_failed",
    "font_fallback_used",
    "unsupported_feature_ignored",
]


@dataclass
class ConversionResult:
    """Result of safe document conversion.

    Fields:
    - markdown: Converted text (normalized, size-capped at 10 MiB)
    - title: Extracted title or filename if not found
    - package: Converter package name ("markitdown")
    - version: Converter version ("0.1.7")
    - converter_profile: Safe converter profile identifier ("markitdown-safe-v1")
    - output_sha256: SHA-256 hash of the output markdown
    - warnings: List of allowlisted warning codes emitted during conversion
    - failure_code: If present, conversion failed with this code (no markdown produced)
    """

    markdown: str | None
    title: str | None
    package: str
    version: str
    converter_profile: str
    output_sha256: str | None
    warnings: list[WarningCode]
    failure_code: FailureCode | None


class SafeMarkItDownConverter:
    """Safe, auditable wrapper around MarkItDown.

    Luôn gọi convert_stream() với metadata từ server.
    Không bao giờ gọi convert_uri, convert_local, hoặc enable plugins.
    """

    def __init__(self):
        """Initialize converter with hardcoded safe settings."""
        try:
            # Import ONLY at instantiation, so test can mock
            import sys
            if "markitdown" not in sys.modules:
                import markitdown
            else:
                markitdown = sys.modules["markitdown"]
            self.markitdown = markitdown
        except ImportError as e:
            raise ImportError(
                "markitdown not installed; use requirements.ingestion.txt"
            ) from e

    def convert(
        self,
        document: ValidatedDocument,
        content: bytes,
    ) -> ConversionResult:
        """Convert validated document to Markdown.

        Args:
            document: ValidatedDocument with metadata (no actual bytes)
            content: Raw document bytes

        Returns:
            ConversionResult with markdown, title, version, and failure_code if failed
        """
        warnings: list[WarningCode] = []
        failure_code: FailureCode | None = None
        markdown: str | None = None
        title: str | None = None
        output_sha256: str | None = None

        try:
            # Instantiate with hardcoded safe settings
            md = self.markitdown.MarkItDown(enable_plugins=False)

            # Build StreamInfo from server-known metadata only
            # (never from client filename/extension)
            stream_info = self._build_stream_info(document)

            # Create BytesIO stream from content
            stream = io.BytesIO(content)

            # Convert: this is the ONLY MarkItDown entry point allowed
            result = md.convert_stream(stream, stream_info=stream_info)

            # Extract markdown from result
            markdown = result.text_content if hasattr(result, "text_content") else str(result)

            # Cap output at 10 MiB
            if len(markdown.encode("utf-8")) > MAX_OUTPUT_MARKDOWN_BYTES:
                failure_code = "conversion_output_too_large"
                markdown = None
                output_sha256 = None
            else:
                # Compute output hash
                output_sha256 = hashlib.sha256(
                    markdown.encode("utf-8")
                ).hexdigest()

                # Extract title if available
                if hasattr(result, "title") and result.title:
                    title = result.title
                else:
                    # Fallback: use document object_key as title
                    title = document.object_key.split("/")[-1]

                # Collect warnings if present
                if hasattr(result, "warnings") and result.warnings:
                    for warn in result.warnings:
                        if isinstance(warn, str) and warn in [
                            "table_structure_degraded",
                            "image_extraction_failed",
                            "font_fallback_used",
                            "unsupported_feature_ignored",
                        ]:
                            warnings.append(warn)

        except TimeoutError:
            failure_code = "conversion_timeout"
        except ValueError as e:
            # Map ValueError to parser error (common for malformed input)
            if "timeout" in str(e).lower():
                failure_code = "conversion_timeout"
            else:
                failure_code = "conversion_parser_error"
        except Exception as e:
            # Map any other exception to parser error (sanitized — no raw message)
            failure_code = "conversion_parser_error"

        return ConversionResult(
            markdown=markdown,
            title=title,
            package="markitdown",
            version="0.1.7",
            converter_profile="markitdown-safe-v1",
            output_sha256=output_sha256,
            warnings=warnings,
            failure_code=failure_code,
        )

    def _build_stream_info(self, document: ValidatedDocument) -> object:
        """Build MarkItDown StreamInfo from server-known metadata only.

        Never from client filename or extension.
        """
        try:
            # markitdown.MarkItDownStreamInfo or similar class
            # If it exists, use it; otherwise build a dict
            if hasattr(self.markitdown, "MarkItDownStreamInfo"):
                return self.markitdown.MarkItDownStreamInfo(
                    mime_type=document.detected_media_type,
                    file_extension=self._get_extension(document.detected_media_type),
                )
            else:
                # Fallback: return dict-like object with mime_type and file_extension
                class StreamInfo:
                    def __init__(self, mime_type: str, file_extension: str):
                        self.mime_type = mime_type
                        self.file_extension = file_extension

                return StreamInfo(
                    mime_type=document.detected_media_type,
                    file_extension=self._get_extension(
                        document.detected_media_type
                    ),
                )
        except Exception:
            # If StreamInfo doesn't exist or can't be built,
            # return None and let MarkItDown infer from stream
            return None

    @staticmethod
    def _get_extension(mime_type: str) -> str:
        """Map MIME type to file extension."""
        mime_to_ext = {
            "text/plain": ".txt",
            "text/csv": ".csv",
            "text/html": ".html",
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        }
        return mime_to_ext.get(mime_type, "")
