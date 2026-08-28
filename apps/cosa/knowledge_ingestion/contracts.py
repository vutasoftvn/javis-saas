"""Untrusted document contracts and upload policies."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

__all__ = [
    "UploadTicket",
    "QuarantinedObject",
    "CreateKnowledgeUploadRequest",
    "CompleteKnowledgeUploadRequest",
    "MIME_TYPE_LIMITS",
    "FailureCode",
    "FEATURE_FLAG_ENV",
    "knowledge_ingestion_enabled",
    "CONVERTER_PACKAGE_SPEC",
    "CONVERTER_PROFILE",
    "CONVERTER_VERSION",
    "QUARANTINE_PREFIX",
    "IngestionMetricEvent",
]

# Fail-closed feature flag — kiểm tra CHUNG ở cả ticket issuance (API) lẫn worker start.
# Mặc định OFF; chỉ bật khi giá trị rõ ràng là true/1/yes.
FEATURE_FLAG_ENV = "KNOWLEDGE_INGESTION_ENABLED"


def knowledge_ingestion_enabled() -> bool:
    """True chỉ khi FEATURE_FLAG_ENV được set tường minh về true/1/yes (fail-closed)."""
    return os.environ.get(FEATURE_FLAG_ENV, "false").strip().lower() in ("true", "1", "yes")


# Bản pin DUY NHẤT của converter — readiness gate so khớp env deploy với hằng này
# để chặn việc vô tình deploy `markitdown[all]` hoặc bật plugins.
CONVERTER_PACKAGE_SPEC = "markitdown[pdf,docx,pptx,xlsx]==0.1.7"
CONVERTER_PROFILE = "markitdown-safe-v1"
CONVERTER_VERSION = "0.1.7"

# Prefix bắt buộc cho mọi object key trong quarantine store (server-owned, scoped).
QUARANTINE_PREFIX = "quarantine/"

# Canonical failure codes for document validation, scanning, and conversion
FailureCode = Literal[
    "unsupported_media_type",
    "mime_mismatch",
    "file_too_large",
    "archive_limit_exceeded",
    "malware_detected",
    "scanner_unavailable",
    "checksum_mismatch",
    "conversion_timeout",
    "conversion_output_too_large",
    "conversion_parser_error",
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


@dataclass
class IngestionMetricEvent:
    """Sự kiện metric/state-transition đã sanitize cho quan sát pipeline.

    Schema CỐ ĐỊNH — KHÔNG được mang nội dung tài liệu, object key, signed URL,
    parser traceback hay scanner body. Chỉ id, tenant, trạng thái, loại/kích thước,
    thời lượng và mã lỗi/cảnh báo trong allowlist.
    """

    ingestion_id: str
    workspace_id: str
    state: str
    detected_media_type: str
    size_bytes: int
    duration_ms: int
    failure_code: Optional[FailureCode] = None
    warning_codes: list[str] = field(default_factory=list)

    # Các khoá bị cấm tuyệt đối — dùng để test/guard chống rò rỉ nếu ai đó mở rộng sai.
    _FORBIDDEN_KEYS = frozenset(
        {"markdown", "content", "object_key", "signed_url", "traceback", "scanner_body", "text"}
    )

    def to_dict(self) -> dict:
        payload: dict = {
            "ingestion_id": self.ingestion_id,
            "workspace_id": self.workspace_id,
            "state": self.state,
            "detected_media_type": self.detected_media_type,
            "size_bytes": self.size_bytes,
            "duration_ms": self.duration_ms,
        }
        if self.failure_code is not None:
            payload["failure_code"] = self.failure_code
        if self.warning_codes:
            payload["warning_codes"] = list(self.warning_codes)
        assert self._FORBIDDEN_KEYS.isdisjoint(payload.keys()), "metric event leaked a forbidden key"
        return payload
