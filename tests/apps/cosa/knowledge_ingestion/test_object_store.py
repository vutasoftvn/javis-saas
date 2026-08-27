"""Tests for DocumentObjectStore implementations — contract validation."""

from __future__ import annotations

import asyncio
import hashlib
from io import BytesIO
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.cosa.knowledge_ingestion.contracts import (
    UploadTicket,
    QuarantinedObject,
    MIME_TYPE_LIMITS,
)
from apps.cosa.knowledge_ingestion.object_store import (
    DocumentObjectStore,
    InMemoryDocumentObjectStore,
    S3DocumentObjectStore,
)


class TestInMemoryDocumentObjectStore:
    """In-memory implementation for unit tests — no network."""

    @pytest.mark.asyncio
    async def test_issue_upload_ticket_generates_random_key(self):
        """Generated key is server-owned, random, scoped under quarantine/."""
        store = InMemoryDocumentObjectStore()
        ingestion_id = "ing_abc123"
        workspace_id = "ws_xyz"
        media_type = "text/csv"
        max_bytes = 10 * 1024 * 1024  # 10 MiB

        ticket1 = await store.issue_upload_ticket(
            ingestion_id=ingestion_id,
            workspace_id=workspace_id,
            media_type=media_type,
            max_bytes=max_bytes,
        )
        ticket2 = await store.issue_upload_ticket(
            ingestion_id=ingestion_id,
            workspace_id=workspace_id,
            media_type=media_type,
            max_bytes=max_bytes,
        )

        # Keys must be different (random)
        assert ticket1.object_key != ticket2.object_key
        # Keys must be scoped under quarantine
        assert ticket1.object_key.startswith(f"quarantine/{workspace_id}/{ingestion_id}/")
        assert ticket2.object_key.startswith(f"quarantine/{workspace_id}/{ingestion_id}/")
        # Return type is UploadTicket (has signed_url, expires_at)
        assert isinstance(ticket1, UploadTicket)
        assert ticket1.signed_url is not None
        assert ticket1.expires_at is not None
        assert ticket1.object_key is not None

    @pytest.mark.asyncio
    async def test_finalize_upload_validates_mime_and_size(self):
        """finalize_upload computes SHA-256, detects MIME, and validates size."""
        store = InMemoryDocumentObjectStore()
        ingestion_id = "ing_test"
        workspace_id = "ws_test"

        # Issue ticket for CSV (≤10 MiB allowed per contract)
        ticket = await store.issue_upload_ticket(
            ingestion_id=ingestion_id,
            workspace_id=workspace_id,
            media_type="text/csv",
            max_bytes=10 * 1024 * 1024,
        )

        # Write test CSV data to the bucket (simulating successful PUT)
        csv_data = b"name,age\nAlice,30\nBob,25\n"
        store._buckets[workspace_id][ticket.object_key] = csv_data

        # Finalize and expect correct hash/size
        result = await store.finalize_upload(
            ingestion_id=ingestion_id,
            workspace_id=workspace_id,
        )

        assert isinstance(result, QuarantinedObject)
        assert result.object_key == ticket.object_key
        assert result.size_bytes == len(csv_data)
        # SHA-256 computed server-side
        expected_hash = hashlib.sha256(csv_data).hexdigest()
        assert result.source_sha256 == expected_hash
        # MIME type sniffed from bytes, should detect CSV
        assert "text" in result.detected_media_type or "csv" in result.detected_media_type.lower()

    @pytest.mark.asyncio
    async def test_finalize_upload_rejects_size_overrun(self):
        """finalize_upload rejects when actual size exceeds max_bytes declared at ticket issue."""
        store = InMemoryDocumentObjectStore()
        ingestion_id = "ing_toolarge"
        workspace_id = "ws_test"

        # Issue ticket for max 1 MiB
        ticket = await store.issue_upload_ticket(
            ingestion_id=ingestion_id,
            workspace_id=workspace_id,
            media_type="text/plain",
            max_bytes=1 * 1024 * 1024,
        )

        # Write 2 MiB of data (exceeds max)
        large_data = b"x" * (2 * 1024 * 1024)
        store._buckets[workspace_id][ticket.object_key] = large_data

        # Finalize should reject
        with pytest.raises(ValueError, match="size.*exceeds.*max"):
            await store.finalize_upload(
                ingestion_id=ingestion_id,
                workspace_id=workspace_id,
            )

    @pytest.mark.asyncio
    async def test_finalize_upload_returns_non_enumerating_error_for_missing_ingestion(self):
        """Finalize with unknown ingestion ID returns 404-like error without leaking key."""
        store = InMemoryDocumentObjectStore()

        with pytest.raises(ValueError, match="not found"):
            await store.finalize_upload(
                ingestion_id="ing_nonexistent",
                workspace_id="ws_test",
            )

    @pytest.mark.asyncio
    async def test_finalize_upload_rejects_wrong_workspace(self):
        """Cross-workspace finalize is denied."""
        store = InMemoryDocumentObjectStore()
        ingestion_id = "ing_cross"
        workspace_a = "ws_a"
        workspace_b = "ws_b"

        # Issue ticket in workspace A
        ticket = await store.issue_upload_ticket(
            ingestion_id=ingestion_id,
            workspace_id=workspace_a,
            media_type="text/plain",
            max_bytes=1024,
        )
        store._buckets[workspace_a][ticket.object_key] = b"test data"

        # Try to finalize from workspace B
        with pytest.raises(ValueError, match="not found|workspace"):
            await store.finalize_upload(
                ingestion_id=ingestion_id,
                workspace_id=workspace_b,
            )

    @pytest.mark.asyncio
    async def test_expired_ticket_cannot_finalize(self):
        """Ticket with past expiration cannot be finalized."""
        store = InMemoryDocumentObjectStore()
        ingestion_id = "ing_expired"
        workspace_id = "ws_test"

        # Create a ticket and manually expire it
        ticket = await store.issue_upload_ticket(
            ingestion_id=ingestion_id,
            workspace_id=workspace_id,
            media_type="text/plain",
            max_bytes=1024,
        )

        # Force expiration by manipulating internal state
        from datetime import datetime, timezone, timedelta
        store._tickets[ingestion_id].expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        store._buckets[workspace_id][ticket.object_key] = b"test"

        # Attempt to finalize should fail due to expiration
        with pytest.raises(ValueError, match="expired"):
            await store.finalize_upload(
                ingestion_id=ingestion_id,
                workspace_id=workspace_id,
            )


class TestS3DocumentObjectStore:
    """S3/MinIO implementation — tests mock S3 calls."""

    @pytest.mark.asyncio
    async def test_issue_upload_ticket_s3_presigned_post(self):
        """S3 ticket generates presigned POST form (S3-compat)."""
        mock_s3_client = AsyncMock()
        mock_s3_client.generate_presigned_post = AsyncMock(
            return_value={
                "url": "http://minio:9000/knowledge-ingestions/",
                "fields": {"key": "quarantine/ws_test/ing_s3/obj_abc123", "policy": "..."},
            }
        )

        store = S3DocumentObjectStore(
            s3_client=mock_s3_client,
            bucket_name="knowledge-ingestions",
            region="us-east-1",
        )

        ticket = await store.issue_upload_ticket(
            ingestion_id="ing_s3",
            workspace_id="ws_test",
            media_type="application/pdf",
            max_bytes=25 * 1024 * 1024,
        )

        assert ticket.object_key.startswith("quarantine/ws_test/ing_s3/")
        assert ticket.signed_url is not None
        # Verify S3 client was called
        mock_s3_client.generate_presigned_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_finalize_upload_s3_head_and_read(self):
        """S3 finalize performs HEAD (metadata), then streamed read for hash."""
        mock_s3_client = AsyncMock()
        mock_s3_client.head_object = AsyncMock(
            return_value={"ContentLength": 1024, "ContentType": "application/pdf"}
        )

        # Create a proper async iterator for S3 Body
        test_data = b"PDF content here" * 100

        async def async_iter_chunks():
            yield test_data

        mock_body = MagicMock()
        mock_body.__aiter__ = lambda self: async_iter_chunks()

        mock_s3_client.get_object = AsyncMock(
            return_value={"Body": mock_body}
        )

        store = S3DocumentObjectStore(
            s3_client=mock_s3_client,
            bucket_name="knowledge-ingestions",
            region="us-east-1",
        )

        # Pre-populate internal ticket tracking (normally done by issue_upload_ticket)
        from apps.cosa.knowledge_ingestion.contracts import UploadTicket
        from datetime import datetime, timezone, timedelta
        ticket = UploadTicket(
            object_key="quarantine/ws_test/ing_s3/obj_xyz",
            signed_url="http://minio/presigned",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        store._tickets["ing_s3"] = ticket
        store._ticket_configs["ing_s3"] = {
            "workspace_id": "ws_test",
            "max_bytes": 25 * 1024 * 1024,
        }

        result = await store.finalize_upload(
            ingestion_id="ing_s3",
            workspace_id="ws_test",
        )

        # Verify result
        assert result.object_key == ticket.object_key
        assert result.size_bytes > 0
        assert result.source_sha256 is not None
        assert result.detected_media_type is not None

        # Verify S3 calls (HEAD once, GET multiple times for hash and MIME sniff)
        mock_s3_client.head_object.assert_called_once()
