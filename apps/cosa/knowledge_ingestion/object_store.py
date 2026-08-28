"""Server-owned object storage broker for knowledge ingestion."""

from __future__ import annotations

import hashlib
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

from apps.cosa.knowledge_ingestion.contracts import (
    MIME_TYPE_LIMITS,
    QuarantinedObject,
    UploadTicket,
)

__all__ = [
    "DocumentObjectStore",
    "InMemoryDocumentObjectStore",
    "S3DocumentObjectStore",
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
    """In-memory object store for unit tests — no network, no real S3."""

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


class S3DocumentObjectStore(DocumentObjectStore):
    """S3-compatible (MinIO) object store using boto3."""

    def __init__(
        self,
        s3_client=None,
        bucket_name: str = "knowledge-ingestions",
        region: str = "us-east-1",
        endpoint_url: str | None = None,
    ):
        """Initialize S3-compatible store.

        Args:
            s3_client: boto3 S3 client (or mock for testing).
            bucket_name: S3 bucket name.
            region: AWS region.
            endpoint_url: MinIO endpoint URL (e.g., http://127.0.0.1:9000).
        """
        self.s3_client = s3_client
        self.bucket_name = bucket_name
        self.region = region
        self.endpoint_url = endpoint_url
        # Track tickets in memory (similar to in-memory store, but for S3)
        self._tickets: dict[str, UploadTicket] = {}
        self._ticket_configs: dict[str, dict[str, Any]] = {}

    async def issue_upload_ticket(
        self,
        ingestion_id: str,
        workspace_id: str,
        media_type: str,
        max_bytes: int,
    ) -> UploadTicket:
        """Generate presigned POST form for S3 upload."""
        # Generate server-owned key
        random_suffix = uuid.uuid4().hex[:16]
        object_key = f"quarantine/{workspace_id}/{ingestion_id}/{random_suffix}"

        # Generate presigned POST (valid for 1 hour)
        presigned_data = await self._generate_presigned_post(
            object_key=object_key,
            max_bytes=max_bytes,
            expires_in=3600,
        )

        # Expires in 1 hour
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        ticket = UploadTicket(
            object_key=object_key,
            signed_url=presigned_data.get("url", ""),  # S3 form endpoint
            expires_at=expires_at,
        )

        # Store ticket for later finalization
        self._tickets[ingestion_id] = ticket
        self._ticket_configs[ingestion_id] = {
            "workspace_id": workspace_id,
            "max_bytes": max_bytes,
            "presigned_fields": presigned_data.get("fields", {}),
        }

        return ticket

    async def finalize_upload(
        self,
        ingestion_id: str,
        workspace_id: str,
    ) -> QuarantinedObject:
        """Finalize S3 upload — HEAD, stream read, hash, MIME sniff."""
        # Check ticket
        if ingestion_id not in self._tickets:
            raise ValueError(f"Ingestion {ingestion_id} not found")

        ticket = self._tickets[ingestion_id]
        config = self._ticket_configs[ingestion_id]

        # Verify workspace
        if config["workspace_id"] != workspace_id:
            raise ValueError(f"Ingestion {ingestion_id} not found")

        # Check expiration
        if datetime.now(UTC) > ticket.expires_at:
            raise ValueError(f"Upload ticket expired for ingestion {ingestion_id}")

        # HEAD to get metadata
        head_response = await self._head_object(ticket.object_key)
        if head_response is None:
            raise ValueError(f"Upload not completed for ingestion {ingestion_id}")

        size_bytes = head_response.get("ContentLength", 0)
        head_response.get("ContentType", "application/octet-stream")

        # Validate size
        if size_bytes > config["max_bytes"]:
            raise ValueError(f"Upload size {size_bytes} exceeds max {config['max_bytes']} bytes")

        # Stream read and compute hash
        sha256_hash = hashlib.sha256()
        await self._stream_read_and_hash(ticket.object_key, sha256_hash)

        # Sniff MIME from downloaded bytes
        detected_type = await self._sniff_mime_from_s3(ticket.object_key)

        return QuarantinedObject(
            object_key=ticket.object_key,
            size_bytes=size_bytes,
            source_sha256=sha256_hash.hexdigest(),
            detected_media_type=detected_type,
        )

    async def _generate_presigned_post(
        self, object_key: str, max_bytes: int, expires_in: int
    ) -> dict:
        """Generate presigned POST fields (calls S3 client)."""
        if self.s3_client is None:
            raise RuntimeError("S3 client not initialized")

        # For boto3: generate_presigned_post returns {url, fields}
        return await self.s3_client.generate_presigned_post(
            Bucket=self.bucket_name,
            Key=object_key,
            Fields={},
            Conditions=[
                ["content-length-range", 0, max_bytes],
            ],
            ExpiresIn=expires_in,
        )

    async def _head_object(self, object_key: str) -> dict | None:
        """HEAD object to get metadata."""
        if self.s3_client is None:
            return None

        try:
            return await self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key,
            )
        except Exception:
            return None

    async def _stream_read_and_hash(self, object_key: str, sha256_hash) -> None:
        """Stream read object and compute hash."""
        if self.s3_client is None:
            return

        response = await self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=object_key,
        )

        # Stream body in chunks
        async for chunk in response.get("Body", []):
            sha256_hash.update(chunk)

    async def read_object(
        self,
        object_key: str,
        workspace_id: str,
    ) -> bytes:
        """Read quarantined object bytes from S3.

        Verify workspace scope via object_key format: quarantine/<workspace>/<ingestion>/...
        """
        if self.s3_client is None:
            raise ValueError("S3 client not initialized")

        # Verify workspace scope from object_key
        parts = object_key.split("/")
        if len(parts) < 2 or parts[0] != "quarantine" or parts[1] != workspace_id:
            raise ValueError(f"Object workspace mismatch: {object_key}")

        try:
            response = await self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=object_key,
            )

            # Stream read with bounded max size (use largest MIME_TYPE_LIMITS value)
            max_bytes = max(MIME_TYPE_LIMITS.values()) if MIME_TYPE_LIMITS else 25 * 1024 * 1024
            data = b""
            async for chunk in response.get("Body", []):
                data += chunk
                if len(data) > max_bytes:
                    raise ValueError(f"Object exceeds maximum size {max_bytes}")

            return data
        except Exception as e:
            if "not found" in str(e).lower() or isinstance(e, KeyError):
                raise ValueError(f"Object not found: {object_key}") from e
            raise ValueError(f"Failed to read object: {e}") from e

    async def _sniff_mime_from_s3(self, object_key: str) -> str:
        """Download first 8KB and sniff MIME type."""
        if self.s3_client is None:
            return "application/octet-stream"

        try:
            response = await self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Range="bytes=0-8191",  # First 8 KB
            )
            data = b""
            async for chunk in response.get("Body", []):
                data += chunk
                if len(data) >= 8192:
                    break

            # Use in-memory store's sniff logic
            in_mem_store = InMemoryDocumentObjectStore()
            return in_mem_store._sniff_mime_type(data)
        except Exception:
            return "application/octet-stream"
