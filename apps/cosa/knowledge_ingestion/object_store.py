"""Server-owned object storage broker for knowledge ingestion."""

from __future__ import annotations

import hashlib
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

from apps.cosa.knowledge_ingestion.contracts import (
    QuarantinedObject,
    UploadTicket,
)

__all__ = [
    "DocumentObjectStore",
    "InMemoryDocumentObjectStore",
]


class DocumentObjectStore(ABC):
    """Protocol/ABC for server-owned object storage with untrusted document upload.

    Implementations must:
    1. Generate server-owned, random keys scoped under quarantine/<workspace>/<ingestion>/
    2. Issue short-lived signed upload tickets
    3. Finalize uploads with server-authoritative validation (MIME, hash, size)
    """

    @abstractmethod
    async def issue_upload_ticket(
        self,
        ingestion_id: str,
        workspace_id: str,
        media_type: str,
        max_bytes: int,
    ) -> UploadTicket:
        """Issue a short-lived signed upload target.

        Args:
            ingestion_id: opaque identifier for this ingestion (from control-plane).
            workspace_id: tenant scope.
            media_type: client-declared media type (informational; validated at finalize).
            max_bytes: maximum byte count allowed for upload.

        Returns:
            UploadTicket with server-generated object_key (scoped, random) and signed_url.
            Client must PUT/POST to signed_url once; signed_url expires after ticket.expires_at.

        Raises:
            ValueError: if workspace_id or ingestion_id is invalid.
        """
        ...

    @abstractmethod
    async def finalize_upload(
        self,
        ingestion_id: str,
        workspace_id: str,
    ) -> QuarantinedObject:
        """Finalize upload after client PUT completes — validate and compute hashes.

        Server performs:
        - HEAD to check size (reject if exceeds max_bytes from ticket).
        - Streamed read to compute SHA-256.
        - MIME sniff from bytes.
        - Ticket expiration check.

        Args:
            ingestion_id: same as issue_upload_ticket.
            workspace_id: must match tenant scope from ticket.

        Returns:
            QuarantinedObject with server-derived object_key, actual size_bytes, source_sha256,
            and detected_media_type (sniffed from bytes, not from client claim).

        Raises:
            ValueError: if ticket expired, workspace mismatch, size overrun, or upload missing.
        """
        ...

    @abstractmethod
    async def read_object(
        self,
        object_key: str,
        workspace_id: str,
    ) -> bytes:
        """Read quarantined object bytes from storage.

        Lấy toàn bộ bytes của 1 object đã được quarantine. Dùng cho conversion
        pipeline: preflight → scanner → converter cần truy cập dữ liệu gốc.

        Args:
            object_key: server-owned key (from QuarantinedObject.object_key).
            workspace_id: tenant scope (security boundary check).

        Returns:
            Full object bytes as io.BytesIO or bytes.

        Raises:
            ValueError: if object not found, workspace mismatch, or access denied.
        """
        ...


class InMemoryDocumentObjectStore(DocumentObjectStore):
    """In-memory object store for unit tests — no network, no real S3.

    Task 3 (plan local-first-enterprise-knowledge) — S3-compatible storage
    KHÔNG còn là đường production hợp lệ (ADR-LOCAL-FIRST-001: raw file cư
    trú local trên Workspace Runtime Node, xem `workspace_store.py`).
    `is_test_double` cho composition/preflight tự-kiểm tra không âm thầm wire
    class này vào production.
    """

    is_test_double = True

    def __init__(self):
        self._tickets: dict[str, UploadTicket] = {}  # ingestion_id → ticket
        self._ticket_configs: dict[
            str, dict[str, Any]
        ] = {}  # ingestion_id → {workspace_id, max_bytes}
        self._buckets: dict[str, dict[str, bytes]] = {}  # workspace_id → {object_key → data}

    async def issue_upload_ticket(
        self,
        ingestion_id: str,
        workspace_id: str,
        media_type: str,
        max_bytes: int,
    ) -> UploadTicket:
        """Generate random key and ticket (expires in 1 hour for testing)."""
        # Generate random-ish key
        random_suffix = uuid.uuid4().hex[:16]
        object_key = f"quarantine/{workspace_id}/{ingestion_id}/{random_suffix}"

        # Ticket expires in 1 hour
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        ticket = UploadTicket(
            object_key=object_key,
            signed_url=f"http://test-storage/{object_key}",  # Mock signed URL
            expires_at=expires_at,
        )

        self._tickets[ingestion_id] = ticket
        self._ticket_configs[ingestion_id] = {
            "workspace_id": workspace_id,
            "max_bytes": max_bytes,
        }

        # Ensure workspace bucket exists
        if workspace_id not in self._buckets:
            self._buckets[workspace_id] = {}

        return ticket

    async def finalize_upload(
        self,
        ingestion_id: str,
        workspace_id: str,
    ) -> QuarantinedObject:
        """Finalize upload — validate size, compute hash, sniff MIME."""
        # Check if ticket exists
        if ingestion_id not in self._tickets:
            raise ValueError(f"Ingestion {ingestion_id} not found")

        ticket = self._tickets[ingestion_id]
        config = self._ticket_configs[ingestion_id]

        # Check workspace match
        if config["workspace_id"] != workspace_id:
            raise ValueError(f"Ingestion {ingestion_id} not found")

        # Check ticket expiration
        if datetime.now(UTC) > ticket.expires_at:
            raise ValueError(f"Upload ticket expired for ingestion {ingestion_id}")

        # Check if object was uploaded
        bucket = self._buckets.get(workspace_id, {})
        if ticket.object_key not in bucket:
            raise ValueError(f"Upload not completed for ingestion {ingestion_id}")

        data = bucket[ticket.object_key]

        # Check size
        max_bytes = config["max_bytes"]
        if len(data) > max_bytes:
            raise ValueError(f"Upload size {len(data)} exceeds max {max_bytes} bytes")

        # Compute SHA-256
        sha256 = hashlib.sha256(data).hexdigest()

        # Sniff MIME type
        detected_type = self._sniff_mime_type(data)

        return QuarantinedObject(
            object_key=ticket.object_key,
            size_bytes=len(data),
            source_sha256=sha256,
            detected_media_type=detected_type,
        )

    async def read_object(
        self,
        object_key: str,
        workspace_id: str,
    ) -> bytes:
        """Read quarantined object bytes from in-memory storage."""
        bucket = self._buckets.get(workspace_id, {})
        if object_key not in bucket:
            raise ValueError(f"Object not found: {object_key}")
        return bucket[object_key]

    def _sniff_mime_type(self, data: bytes) -> str:
        """Simple MIME type sniff based on magic bytes."""
        if data.startswith(b"%PDF"):
            return "application/pdf"
        if data.startswith(b"PK\x03\x04"):  # ZIP magic (DOCX, XLSX, PPTX)
            # Could be DOCX, XLSX, or PPTX — return generic for now
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
            return "text/plain; charset=utf-16"
        # Default: treat as CSV/text
        try:
            # Try to decode as UTF-8
            data.decode("utf-8")
            # Check if it looks like CSV
            if b"," in data or b"\n" in data:
                return "text/csv"
            return "text/plain"
        except UnicodeDecodeError:
            return "application/octet-stream"


