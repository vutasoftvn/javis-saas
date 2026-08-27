"""Untrusted document contracts and upload policies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

__all__ = [
    "UploadTicket",
    "QuarantinedObject",
    "CreateKnowledgeUploadRequest",
    "CompleteKnowledgeUploadRequest",
    "MIME_TYPE_LIMITS",
    "FailureCode",
]

# Canonical failure codes for document validation and scanning
FailureCode = Literal[
    "unsupported_media_type",
    "mime_mismatch",
    "file_too_large",
    "archive_limit_exceeded",
    "malware_detected",
    "scanner_unavailable",
    "checksum_mismatch",
]


# Allowlisted MIME types and size limits per the brief
MIME_TYPE_LIMITS: dict[str, int] = {
    "text/plain": 10 * 1024 * 1024,  # 10 MiB
    "text/csv": 10 * 1024 * 1024,  # 10 MiB
    "text/html": 10 * 1024 * 1024,  # 10 MiB
    "application/pdf": 25 * 1024 * 1024,  # 25 MiB
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": 25 * 1024 * 1024,  # DOCX
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": 25 * 1024 * 1024,  # XLSX
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": 25 * 1024 * 1024,  # PPTX
}

# Short aliases for MIME type matching
MIME_ALIASES = {
    "text/x-csv": "text/csv",
    "application/x-csv": "text/csv",
    "application/vnd.ms-excel": 25 * 1024 * 1024,  # XLS (treat as XLSX size limit)
}


@dataclass
class UploadTicket:
    """Short-lived signed upload target — server-owned key, client-supplied via signed URL.

    - `object_key`: server-generated, immutable, random-ish, scoped under
      `quarantine/<workspace>/<ingestion>/`. Never visible to client after this
      response is sent.
    - `signed_url`: presigned PUT/POST target for one-time upload. Client receives
      this ticket and uses it to PUT/POST the file. After upload completes, signed_url
      expires and is no longer valid.
    - `expires_at`: UTC deadline. After this, ticket cannot be used for upload or finalize.
    """

    object_key: str
    signed_url: str
    expires_at: datetime


@dataclass
class QuarantinedObject:
    """Result of server-authoritative finalization after successful upload.

    - `object_key`: same as the ticket's key; server-derived, never from client.
    - `size_bytes`: actual byte count read from storage (server HEAD + stream).
    - `source_sha256`: SHA-256 hash computed server-side during finalization.
    - `detected_media_type`: MIME sniffed from file bytes; may differ from declared type.
    """

    object_key: str
    size_bytes: int
    source_sha256: str
    detected_media_type: str


class CreateKnowledgeUploadRequest:
    """Request contract for initiating a knowledge ingestion upload.

    Fields:
    - `file_name`: client-supplied original filename (informational only).
    - `declared_media_type`: client's MIME type claim (validated server-side at finalize).
    - `idempotency_key`: ensures idempotent creation (passed to services/cosa endpoint).
    """

    def __init__(self, file_name: str, declared_media_type: str, idempotency_key: str):
        self.file_name = file_name
        self.declared_media_type = declared_media_type
        self.idempotency_key = idempotency_key


class CompleteKnowledgeUploadRequest:
    """Request contract for finalizing a knowledge ingestion upload.

    Fields:
    - `ingestion_id`: reference to the DocumentIngestionRecord created earlier.
      Comes from path (:ingestion_id), not from request body.
    """

    def __init__(self, ingestion_id: str):
        self.ingestion_id = ingestion_id
