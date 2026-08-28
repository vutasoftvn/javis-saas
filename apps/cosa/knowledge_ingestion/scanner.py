"""Document malware scanner interface and implementations.

Provides abstraction for malware scanning with:
- Pluggable scanner implementations
- Verdicts: clean | infected | unavailable
- Production readiness guard (rejects fake scanners in production)

Scanners operate on streams and must NOT proceed if verdict != "clean".
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO, Literal

from apps.cosa.knowledge_ingestion.contracts import QuarantinedObject

__all__ = [
    "DocumentMalwareScanner",
    "FakeDocumentMalwareScanner",
    "ScanVerdict",
    "assert_production_scanner_ready",
]

# Scanner verdict type
ScanVerdict = Literal["clean", "infected", "unavailable"]


class DocumentMalwareScanner(ABC):
    """Protocol/ABC for document malware scanning.

    Implementations should handle stream-based scanning without extracting
    documents to filesystem.
    """

    @abstractmethod
    async def scan(self, stream: BinaryIO, document: QuarantinedObject) -> ScanVerdict:
        """
        Scan document for malware.

        Kiểm tra document có malware không.

        Args:
            stream: Document byte stream (seekable, positioned at 0)
            document: Metadata of the quarantined document

        Returns:
            "clean": document is safe
            "infected": malware/suspicious patterns detected
            "unavailable": scanner service down/timeout (treat like infected)
        """
        ...


class FakeDocumentMalwareScanner(DocumentMalwareScanner):
    """Deterministic test/development scanner (never use in production).

    Dùng cho testing; luôn trả về verdict được config sẵn.
    """

    def __init__(self, verdict: ScanVerdict = "clean"):
        """
        Create fake scanner with fixed verdict.

        Args:
            verdict: "clean", "infected", or "unavailable"
        """
        self.verdict = verdict
        self._is_production_safe = False  # Mark as unsafe for production

    async def scan(self, stream: BinaryIO, document: QuarantinedObject) -> ScanVerdict:
        """Return pre-configured verdict without actually scanning."""
        # In a real implementation, this would perform actual scanning.
        # This fake version is for testing only.
        return self.verdict


def assert_production_scanner_ready(
    scanner: DocumentMalwareScanner | None, environment: str
) -> None:
    """
    Verify scanner is production-safe for the given environment.

    Kiểm tra scanner có an toàn cho environment này không.
    Reject fake scanners and None (unconfigured) in production environments.

    Args:
        scanner: DocumentMalwareScanner instance to validate (or None)
        environment: "production", "staging", "development", "test"

    Raises:
        RuntimeError: If scanner is None or fake in production
    """
    if environment != "production":
        # Non-production environments allow fake scanner and None
        return

    # Production: fail closed on unconfigured scanner
    if scanner is None:
        raise RuntimeError(
            "Production requires a configured malware scanner, got None. "
            "Ensure a real scanner (e.g., ClamAV, VirusTotal) is properly initialized."
        )

    # Production: fail closed on fake scanner
    if isinstance(scanner, FakeDocumentMalwareScanner):
        raise RuntimeError(
            "Cannot use FakeDocumentMalwareScanner in production environment. "
            "A real production scanner (e.g., ClamAV, VirusTotal) must be configured."
        )
