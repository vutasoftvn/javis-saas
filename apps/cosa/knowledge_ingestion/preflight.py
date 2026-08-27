"""Security preflight validation for untrusted documents.

Validates documents BEFORE conversion:
- MIME type allowlist enforcement
- Magic byte verification
- File size limits per type
- Checksum integrity
- Office archive (ZIP) bomb detection
- No parsing or extraction to filesystem

Failure codes (mutually exclusive rejection reasons):
- unsupported_media_type: MIME not in MIME_TYPE_LIMITS allowlist
- mime_mismatch: Magic bytes don't match declared type
- file_too_large: File exceeds size limit for its type
- archive_limit_exceeded: Office archive violates safety constraints
- checksum_mismatch: SHA-256 recomputation doesn't match provided hash
"""

from __future__ import annotations

import hashlib
import zipfile
from dataclasses import dataclass
from typing import BinaryIO, Literal

from apps.cosa.knowledge_ingestion.contracts import (
    MIME_TYPE_LIMITS,
    QuarantinedObject,
)

__all__ = [
    "ValidatedDocument",
    "validate_quarantined_object",
    "preflight_office_archive",
    "ArchiveSafetyReport",
]

# Failure codes (exactly as specified in brief)
FailureCode = Literal[
    "unsupported_media_type",
    "mime_mismatch",
    "file_too_large",
    "archive_limit_exceeded",
    "checksum_mismatch",
]


@dataclass
class ArchiveSafetyReport:
    """Result of Office archive safety inspection."""

    is_safe: bool
    reason: str | None = None
    member_count: int = 0
    total_uncompressed_bytes: int = 0
    max_member_uncompressed: int = 0
    compression_ratio: float = 0.0


@dataclass
class ValidatedDocument:
    """Safe document reference after preflight validation.

    Fields safe to pass onward to conversion layer.
    """

    object_key: str
    detected_media_type: str  # Allowlisted MIME type
    source_sha256: str
    size_bytes: int
    # Stream handle/factory for converter to use later (minimal, no parser inference)
    # This is passed as-is; converter will need to re-open from object store if needed


def _get_magic_bytes(stream: BinaryIO, num_bytes: int = 16) -> bytes:
    """Read initial magic bytes without consuming the stream."""
    current_pos = stream.tell()
    magic = stream.read(num_bytes)
    stream.seek(current_pos)
    return magic


def _check_mime_magic_match(mime_type: str, magic_bytes: bytes) -> bool:
    """
    Verify magic bytes align with claimed MIME type.

    Kiểm tra magic bytes có phù hợp với MIME type được claim.
    """
    if mime_type == "application/pdf":
        # PDF files start with %PDF-
        return magic_bytes.startswith(b"%PDF-")

    elif mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ):
        # Office formats are ZIP archives: start with PK\x03\x04
        return magic_bytes.startswith(b"PK\x03\x04")

    elif mime_type in ("text/plain", "text/csv", "text/html"):
        # Text formats are generally ASCII/UTF-8; accept without strict magic check
        # These formats don't have rigid magic byte signatures
        # Just verify they're not binary data (not starting with common binary markers)
        # Accept if it doesn't look like a ZIP, PDF, or other binary format
        if magic_bytes.startswith(b"PK\x03\x04"):  # ZIP
            return False
        if magic_bytes.startswith(b"%PDF-"):  # PDF
            return False
        # Text formats can start with various characters; don't be overly strict
        return True

    # Unknown MIME type (shouldn't reach here if allowlist check ran first)
    return True


def _bounded_read_and_hash(
    stream: BinaryIO, size_limit: int, chunk_size: int = 8192
) -> tuple[int, str, bytes]:
    """
    Read stream in chunks up to size_limit, compute SHA-256, return bytes for validation.

    Đọc stream từng chunk, tính SHA-256, kiểm tra kích thước.
    Dừng ngay khi vượt quá limit (không buffer unlimited bytes).

    Returns: (bytes_read, sha256_hex, initial_bytes_for_magic_check)
    """
    hasher = hashlib.sha256()
    bytes_read = 0
    all_bytes = b""

    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break

        bytes_read += len(chunk)
        if bytes_read > size_limit:
            # Exceeded limit - reject immediately
            raise ValueError(f"file_too_large")

        hasher.update(chunk)
        if len(all_bytes) < 32:  # Keep first 32 bytes for magic check
            all_bytes += chunk

    return bytes_read, hasher.hexdigest(), all_bytes


def preflight_office_archive(stream: BinaryIO) -> ArchiveSafetyReport:
    """
    Inspect Office archive (DOCX/XLSX/PPTX) for bomb vectors.

    Inspects ZIP central directory WITHOUT extracting to filesystem.
    Kiểm tra archive mà không giải nén ra filesystem.

    Enforces:
    - Member count ≤ 1,000
    - Total uncompressed size ≤ 100 MiB
    - Single member uncompressed ≤ 50 MiB
    - Compression ratio ≤ 20:1

    Returns ArchiveSafetyReport with is_safe=True or False + reason.
    """
    try:
        # Save current position to rewind after inspection
        start_pos = stream.tell()

        with zipfile.ZipFile(stream, "r") as zf:
            member_count = len(zf.infolist())
            total_uncompressed = 0
            max_member_uncompressed = 0
            total_compressed = 0

            # Inspect central directory only; never call .read()/.extract()
            for info in zf.infolist():
                uncompressed = info.file_size
                compressed = info.compress_size

                total_uncompressed += uncompressed
                total_compressed += compressed

                if uncompressed > max_member_uncompressed:
                    max_member_uncompressed = uncompressed

                # Check individual member limit (50 MiB)
                if uncompressed > 50 * 1024 * 1024:
                    return ArchiveSafetyReport(
                        is_safe=False,
                        reason=f"archive_limit_exceeded: member {info.filename} uncompressed size {uncompressed} exceeds 50 MiB",
                        member_count=member_count,
                        total_uncompressed_bytes=total_uncompressed,
                        max_member_uncompressed=max_member_uncompressed,
                    )

            # Check member count limit (1,000 members)
            if member_count > 1000:
                return ArchiveSafetyReport(
                    is_safe=False,
                    reason=f"archive_limit_exceeded: {member_count} members exceeds 1,000",
                    member_count=member_count,
                    total_uncompressed_bytes=total_uncompressed,
                    max_member_uncompressed=max_member_uncompressed,
                )

            # Check total uncompressed size (100 MiB)
            if total_uncompressed > 100 * 1024 * 1024:
                return ArchiveSafetyReport(
                    is_safe=False,
                    reason=f"archive_limit_exceeded: total uncompressed {total_uncompressed} exceeds 100 MiB",
                    member_count=member_count,
                    total_uncompressed_bytes=total_uncompressed,
                    max_member_uncompressed=max_member_uncompressed,
                )

            # Check compression ratio (20:1 max)
            # Only if there's actual compressed data
            if total_compressed > 0:
                ratio = total_uncompressed / total_compressed
                if ratio > 20.0:
                    return ArchiveSafetyReport(
                        is_safe=False,
                        reason=f"archive_limit_exceeded: compression ratio {ratio:.1f}:1 exceeds 20:1",
                        member_count=member_count,
                        total_uncompressed_bytes=total_uncompressed,
                        max_member_uncompressed=max_member_uncompressed,
                        compression_ratio=ratio,
                    )

            # All checks passed
            return ArchiveSafetyReport(
                is_safe=True,
                member_count=member_count,
                total_uncompressed_bytes=total_uncompressed,
                max_member_uncompressed=max_member_uncompressed,
                compression_ratio=total_uncompressed / total_compressed
                if total_compressed > 0
                else 0.0,
            )

    except zipfile.BadZipFile as e:
        return ArchiveSafetyReport(
            is_safe=False,
            reason=f"mime_mismatch: not a valid ZIP archive: {e}",
        )
    finally:
        # Always rewind to start position
        stream.seek(start_pos)


def validate_quarantined_object(
    obj: QuarantinedObject, stream: BinaryIO
) -> ValidatedDocument:
    """
    Validate quarantined document before conversion.

    Kiểm tra document trước khi chuyển đổi:
    1. MIME type in allowlist
    2. Magic bytes match claimed type
    3. File size within limit
    4. SHA-256 matches
    5. For Office archives: no bomb vectors

    Args:
        obj: QuarantinedObject with metadata
        stream: Binary stream of document bytes (position at 0)

    Returns:
        ValidatedDocument if all checks pass

    Raises:
        ValueError with failure code if any check fails:
        - unsupported_media_type
        - mime_mismatch
        - file_too_large
        - archive_limit_exceeded
        - checksum_mismatch
    """
    detected_mime = obj.detected_media_type

    # Step 1: Check MIME type is in allowlist
    if detected_mime not in MIME_TYPE_LIMITS:
        raise ValueError(f"unsupported_media_type: {detected_mime}")

    size_limit = MIME_TYPE_LIMITS[detected_mime]

    # Step 2: Check magic bytes
    magic_bytes = _get_magic_bytes(stream)
    if not _check_mime_magic_match(detected_mime, magic_bytes):
        raise ValueError(
            f"mime_mismatch: magic bytes don't match {detected_mime}"
        )

    # Step 3: Bounded read + size check + hash computation
    bytes_read = 0
    computed_hash = ""
    try:
        bytes_read, computed_hash, _ = _bounded_read_and_hash(stream, size_limit)
    except ValueError as e:
        if "file_too_large" in str(e):
            raise ValueError(f"file_too_large: {bytes_read} exceeds {size_limit}")
        raise

    # Step 4: Check SHA-256 matches
    if computed_hash != obj.source_sha256:
        raise ValueError(
            f"checksum_mismatch: computed {computed_hash}, expected {obj.source_sha256}"
        )

    # Step 5: For Office archives, check for bomb vectors
    if detected_mime in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ):
        stream.seek(0)  # Reset to start
        archive_report = preflight_office_archive(stream)
        if not archive_report.is_safe:
            raise ValueError(f"{archive_report.reason}")

    # All checks passed
    return ValidatedDocument(
        object_key=obj.object_key,
        detected_media_type=detected_mime,
        source_sha256=computed_hash,
        size_bytes=bytes_read,
    )
