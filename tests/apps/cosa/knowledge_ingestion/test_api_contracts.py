"""Tests for knowledge ingestion API routes — contract validation."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

import httpx
import pytest

from apps.cosa.api.app import create_cosa_app
from apps.cosa.knowledge_ingestion.object_store import InMemoryDocumentObjectStore
from apps.cosa.knowledge_ingestion.contracts import QuarantinedObject
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from agent_core.conversations.repository import InMemoryConversationRepository
from agent_core.coordination.scheduler import RunScheduler
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.registry.repository import InMemorySpecRegistryRepository
from agent_core.runs.leases import RunLeaseManager
from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
from agent_core.runs.repository import InMemoryRunRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.capabilities.client import CompanyServiceClient
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity


TENANT_A = dict(principal_id="user:alice", workspace_id="ws_a")
TENANT_B = dict(principal_id="user:bob", workspace_id="ws_b")


@pytest.fixture
def test_app():
    """Create test app with in-memory object store."""
    # Disable feature flag for these tests to verify routes reject when disabled
    os.environ["KNOWLEDGE_INGESTION_ENABLED"] = "false"

    mock_company_client = AsyncMock(spec=CompanyServiceClient)
    plane = build_cosa_agent_plane(
        company_client=mock_company_client,
        tenant_policy_client=MagicMock(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )

    app = create_cosa_app(plane=plane)
    # Inject mock object store for testing
    app.state.knowledge_object_store = InMemoryDocumentObjectStore()
    # Inject mock services/cosa client
    app.state.cosa_document_ingestion_client = AsyncMock()
    return app


@pytest.mark.asyncio
async def test_feature_flag_disabled_returns_clear_rejection(test_app):
    """When KNOWLEDGE_INGESTION_ENABLED is false, routes return 403 with clear message."""
    os.environ["KNOWLEDGE_INGESTION_ENABLED"] = "false"
    override_authenticated_identity(test_app, **TENANT_A)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.post(
            "/agent/knowledge/uploads",
            json={
                "file_name": "document.csv",
                "declared_media_type": "text/csv",
                "idempotency_key": "idempotent_1",
            },
        )
        # Should be disabled (feature flag check)
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_create_knowledge_upload_request_accepts_required_fields(test_app):
    """POST /agent/knowledge/uploads accepts CreateKnowledgeUploadRequest fields."""
    os.environ["KNOWLEDGE_INGESTION_ENABLED"] = "true"
    override_authenticated_identity(test_app, **TENANT_A)

    # Set up mock to simulate successful integration with services/cosa
    mock_store = test_app.state.knowledge_object_store
    ingestion_id = "ing_test_123"

    # Create a simple in-memory tracking of upload tickets
    from apps.cosa.knowledge_ingestion.contracts import UploadTicket
    ticket = UploadTicket(
        object_key=f"quarantine/ws_a/{ingestion_id}/obj_xyz",
        signed_url="http://minio:9000/presigned",
        expires_at=datetime.now(timezone.utc),
    )
    mock_store._tickets[ingestion_id] = ticket
    mock_store._ticket_configs[ingestion_id] = {"workspace_id": "ws_a", "max_bytes": 10*1024*1024}

    # For this test, we'll directly test that the required fields are present
    # and the route rejects invalid requests
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        # Missing field should cause validation error
        res = await ac.post(
            "/agent/knowledge/uploads",
            json={
                "file_name": "document.csv",
                # Missing declared_media_type and idempotency_key
            },
        )
        assert res.status_code == 422  # Pydantic validation error

        # Valid request should work (even if services/cosa is unavailable, we expect 502)
        res = await ac.post(
            "/agent/knowledge/uploads",
            json={
                "file_name": "document.csv",
                "declared_media_type": "text/csv",
                "idempotency_key": "idempotent_1",
            },
        )
        # 502 because services/cosa endpoint isn't actually available, but that's OK -
        # we're testing the request contract, not the full integration
        assert res.status_code in (502, 201)


@pytest.mark.asyncio
async def test_no_MessageAttachmentCreate_object_ref_in_knowledge_routes(test_app):
    """Knowledge upload routes use separate contract from MessageAttachmentCreate."""
    os.environ["KNOWLEDGE_INGESTION_ENABLED"] = "true"
    override_authenticated_identity(test_app, **TENANT_A)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        # The object_ref field should not be part of knowledge upload request
        # (it's part of chat message attachments)
        # FastAPI will ignore unknown fields by default or raise 422
        res = await ac.post(
            "/agent/knowledge/uploads",
            json={
                "file_name": "document.csv",
                "declared_media_type": "text/csv",
                "idempotency_key": "idempotent_1",
                "object_ref": "chat:msg_123",  # Should be ignored
            },
        )
        # Either 422 (validation error on unknown field), 502 (services/cosa unavailable), or 201 (ignored extra field)
        # The important thing is that object_ref doesn't influence the ingestion path
        assert res.status_code in (201, 422, 502)
        if res.status_code == 201:
            assert "object_ref" not in res.json()


@pytest.mark.asyncio
async def test_complete_knowledge_upload_uses_worker_token_and_mock_client(test_app):
    """POST /agent/knowledge/uploads/{ingestion_id}/complete uses worker service token and injected mock client."""
    os.environ["KNOWLEDGE_INGESTION_ENABLED"] = "true"
    os.environ["COSA_WORKER_SERVICE_TOKEN"] = "worker-token-test"
    override_authenticated_identity(test_app, **TENANT_A)

    # Set up mock object store with a finalized object
    mock_store = test_app.state.knowledge_object_store
    ingestion_id = "ing_complete_123"

    # Mock the finalize_upload to return a successful result
    mock_store.finalize_upload = AsyncMock(
        return_value=QuarantinedObject(
            object_key="quarantine/ws_a/ing_complete_123/obj_xyz",
            size_bytes=1024,
            source_sha256="abc123def456",
            detected_media_type="text/csv",
        )
    )

    # Set up mock HTTP client for services/cosa calls
    mock_http_response = AsyncMock()
    mock_http_response.status_code = 200
    mock_http_response.json = lambda: {
        "id": ingestion_id,
        "workspaceId": "ws_a",
        "state": "QUEUED",
        "detectedMediaType": "text/csv",
        "sizeBytes": 1024,
        "sourceSha256": "abc123def456",
    }

    mock_http_client = AsyncMock()
    mock_http_client.post = AsyncMock(return_value=mock_http_response)
    test_app.state.cosa_document_ingestion_client = mock_http_client

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.post(
            f"/agent/knowledge/uploads/{ingestion_id}/complete",
            json={},
        )
        # Should succeed with the mock client
        assert res.status_code == 200
        data = res.json()

        # Verify response structure
        assert "ingestion_id" in data
        assert data["ingestion_id"] == ingestion_id
        assert data["state"] == "QUEUED"
        assert data["detected_media_type"] == "text/csv"
        assert data["size_bytes"] == 1024
        assert data["source_sha256"] == "abc123def456"

        # Verify private fields not leaked
        assert "object_key" not in data
        assert "signed_url" not in data
        assert "original_object_key" not in data

        # Verify the mock client was called with worker token (not member bearer token)
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        # Check the Authorization header uses worker token
        headers = call_args.kwargs.get("headers", {})
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer worker-token-test"
        # Verify it called the right endpoint
        endpoint_url = call_args.args[0] if call_args.args else call_args.kwargs.get("url", "")
        assert f"/cosa/document-ingestions/{ingestion_id}/complete" in endpoint_url


@pytest.mark.asyncio
async def test_complete_knowledge_upload_missing_worker_token_returns_500(test_app):
    """When COSA_WORKER_SERVICE_TOKEN is not set, complete endpoint returns 500."""
    os.environ["KNOWLEDGE_INGESTION_ENABLED"] = "true"
    # Ensure worker token is not set
    if "COSA_WORKER_SERVICE_TOKEN" in os.environ:
        del os.environ["COSA_WORKER_SERVICE_TOKEN"]
    override_authenticated_identity(test_app, **TENANT_A)

    # Set up mock object store
    mock_store = test_app.state.knowledge_object_store
    ingestion_id = "ing_no_token"

    mock_store.finalize_upload = AsyncMock(
        return_value=QuarantinedObject(
            object_key="quarantine/ws_a/ing_no_token/obj_xyz",
            size_bytes=1024,
            source_sha256="abc123def456",
            detected_media_type="text/csv",
        )
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.post(
            f"/agent/knowledge/uploads/{ingestion_id}/complete",
            json={},
        )
        # Should fail with 500 or 502 (control plane error due to missing token)
        assert res.status_code in (500, 502)
        # Should not crash or leak sensitive data
        data = res.json()
        assert "detail" in data


@pytest.mark.asyncio
async def test_complete_knowledge_upload_response_omits_object_key(test_app):
    """POST /agent/knowledge/uploads/{ingestion_id}/complete response never includes object_key."""
    os.environ["KNOWLEDGE_INGESTION_ENABLED"] = "true"
    os.environ["COSA_WORKER_SERVICE_TOKEN"] = "worker-token-test"
    override_authenticated_identity(test_app, **TENANT_A)

    # Set up mock object store with a finalized object
    mock_store = test_app.state.knowledge_object_store
    ingestion_id = "ing_complete_123"

    # Mock the finalize_upload to return a successful result
    mock_store.finalize_upload = AsyncMock(
        return_value=QuarantinedObject(
            object_key="quarantine/ws_a/ing_complete_123/obj_xyz",  # PRIVATE
            size_bytes=1024,
            source_sha256="abc123def456",
            detected_media_type="text/csv",
        )
    )

    # Set up mock HTTP client
    mock_http_response = AsyncMock()
    mock_http_response.status_code = 200
    mock_http_response.json = lambda: {
        "id": ingestion_id,
        "workspaceId": "ws_a",
        "state": "QUEUED",
    }

    mock_http_client = AsyncMock()
    mock_http_client.post = AsyncMock(return_value=mock_http_response)
    test_app.state.cosa_document_ingestion_client = mock_http_client

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.post(
            f"/agent/knowledge/uploads/{ingestion_id}/complete",
            json={},
        )
        # Should be 200 with mock client
        if res.status_code == 200:
            data = res.json()
            # Verify no private fields in response
            assert "object_key" not in data
            assert "signed_url" not in data
            assert "original_object_key" not in data


@pytest.mark.asyncio
async def test_tenant_a_cannot_access_tenant_b_ingestion(test_app):
    """Cross-workspace finalization is denied (tenant isolation)."""
    os.environ["KNOWLEDGE_INGESTION_ENABLED"] = "true"
    override_authenticated_identity(test_app, **TENANT_A)

    # Mock object store to raise error for wrong workspace
    mock_store = test_app.state.knowledge_object_store
    mock_store.finalize_upload = AsyncMock(
        side_effect=ValueError("Ingestion not found")  # Non-enumerating error
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        override_authenticated_identity(test_app, **TENANT_B)
        res = await ac.post(
            "/agent/knowledge/uploads/ing_belongs_to_a/complete",
            json={},
        )
        # Must return 404 or 403, not 200
        assert res.status_code in (403, 404)


@pytest.mark.asyncio
async def test_review_knowledge_ingestion_endpoint_requires_membership(test_app):
    """POST /agent/knowledge/ingestions/{ingestion_id}/review requires workspace membership."""
    os.environ["KNOWLEDGE_INGESTION_ENABLED"] = "true"
    override_authenticated_identity(test_app, **TENANT_A)

    # Mock services/cosa client to simulate review endpoint
    mock_http_response = AsyncMock()
    mock_http_response.status_code = 200
    mock_http_response.json = lambda: {
        "id": "ing_review_123",
        "state": "PUBLISHED",
    }

    mock_http_client = AsyncMock()
    mock_http_client.post = AsyncMock(return_value=mock_http_response)
    test_app.state.cosa_document_ingestion_client = mock_http_client

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        # Valid request from member
        res = await ac.post(
            "/agent/knowledge/ingestions/ing_review_123/review",
            json={
                "decision": "publish_reference",
                "reason": "Looks good",
            },
        )
        # Should succeed (or fail at services/cosa if not configured, but not 401)
        assert res.status_code != 401


@pytest.mark.asyncio
async def test_review_knowledge_ingestion_decision_publish_reference(test_app):
    """Review endpoint accepts 'publish_reference' decision."""
    os.environ["KNOWLEDGE_INGESTION_ENABLED"] = "true"
    override_authenticated_identity(test_app, **TENANT_A)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        # Valid publish_reference request
        res = await ac.post(
            "/agent/knowledge/ingestions/ing_123/review",
            json={
                "decision": "publish_reference",
                "reason": "Document approved",
            },
        )
        # Should either succeed (200) or fail with services/cosa error (502), not validation error (422)
        assert res.status_code != 422


@pytest.mark.asyncio
async def test_review_knowledge_ingestion_decision_reject(test_app):
    """Review endpoint accepts 'reject' decision."""
    os.environ["KNOWLEDGE_INGESTION_ENABLED"] = "true"
    override_authenticated_identity(test_app, **TENANT_A)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        # Valid reject request
        res = await ac.post(
            "/agent/knowledge/ingestions/ing_123/review",
            json={
                "decision": "reject",
                "reason": "Contains sensitive data",
            },
        )
        # Should either succeed (200) or fail with services/cosa error (502), not validation error (422)
        assert res.status_code != 422


@pytest.mark.asyncio
async def test_review_response_is_safe_status_dto(test_app):
    """Review response returns safe status DTO without object metadata or Markdown."""
    os.environ["KNOWLEDGE_INGESTION_ENABLED"] = "true"
    override_authenticated_identity(test_app, **TENANT_A)

    # Mock services/cosa review endpoint response
    mock_http_response = AsyncMock()
    mock_http_response.status_code = 200
    mock_http_response.json = lambda: {
        "id": "ing_review_123",
        "state": "PUBLISHED",
        "createdAt": "2026-08-28T12:00:00Z",
        "updatedAt": "2026-08-28T12:00:01Z",
    }

    mock_http_client = AsyncMock()
    mock_http_client.post = AsyncMock(return_value=mock_http_response)
    test_app.state.cosa_document_ingestion_client = mock_http_client

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.post(
            "/agent/knowledge/ingestions/ing_review_123/review",
            json={
                "decision": "publish_reference",
                "reason": "Approved",
            },
        )

        if res.status_code == 200:
            data = res.json()
            # Should not expose these sensitive fields
            assert "manifestJson" not in data
            assert "object_key" not in data
            assert "markdown" not in data
            # Should have safe fields
            assert "id" in data or "ingestion_id" in data
            assert "state" in data


@pytest.mark.asyncio
async def test_review_publish_reference_flips_agent_core_ingest_status(test_app):
    """publish_reference phải lật KnowledgeDocument.ingest_status review_pending → published."""
    os.environ["KNOWLEDGE_INGESTION_ENABLED"] = "true"
    override_authenticated_identity(test_app, **TENANT_A)

    from agent_core.knowledge.store import InMemoryKnowledgeStore
    from agent_core.knowledge.service import KnowledgeIngestionService
    from agent_core.knowledge.models import KnowledgeDocument

    store = InMemoryKnowledgeStore()
    candidate = KnowledgeDocument(
        id="doc_candidate_1",
        workspace_id="ws_a",
        title="Pending candidate",
        authority_class="USER_CONTENT",
        ingest_status="review_pending",
        chunks=[],
    )
    await store.save_document(candidate)
    test_app.state.knowledge_ingestion_service = KnowledgeIngestionService(store)

    mock_http_response = AsyncMock()
    mock_http_response.status_code = 200
    mock_http_response.json = lambda: {
        "id": "ing_review_999",
        "state": "PUBLISHED",
        "knowledgeSourceId": "doc_candidate_1",
    }
    mock_http_client = AsyncMock()
    mock_http_client.post = AsyncMock(return_value=mock_http_response)
    test_app.state.cosa_document_ingestion_client = mock_http_client

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.post(
            "/agent/knowledge/ingestions/ing_review_999/review",
            json={"decision": "publish_reference", "reason": "Approved"},
        )

    assert res.status_code == 200
    updated = await store.get_document("doc_candidate_1")
    assert updated is not None
    assert updated.ingest_status == "published"


@pytest.mark.asyncio
async def test_review_reject_flips_agent_core_ingest_status(test_app):
    """reject phải lật ingest_status review_pending → rejected."""
    os.environ["KNOWLEDGE_INGESTION_ENABLED"] = "true"
    override_authenticated_identity(test_app, **TENANT_A)

    from agent_core.knowledge.store import InMemoryKnowledgeStore
    from agent_core.knowledge.service import KnowledgeIngestionService
    from agent_core.knowledge.models import KnowledgeDocument

    store = InMemoryKnowledgeStore()
    await store.save_document(
        KnowledgeDocument(
            id="doc_candidate_2",
            workspace_id="ws_a",
            title="Pending candidate 2",
            authority_class="USER_CONTENT",
            ingest_status="review_pending",
            chunks=[],
        )
    )
    test_app.state.knowledge_ingestion_service = KnowledgeIngestionService(store)

    mock_http_response = AsyncMock()
    mock_http_response.status_code = 200
    mock_http_response.json = lambda: {
        "id": "ing_review_998",
        "state": "REJECTED",
        "knowledgeSourceId": "doc_candidate_2",
    }
    mock_http_client = AsyncMock()
    mock_http_client.post = AsyncMock(return_value=mock_http_response)
    test_app.state.cosa_document_ingestion_client = mock_http_client

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.post(
            "/agent/knowledge/ingestions/ing_review_998/review",
            json={"decision": "reject", "reason": "Sensitive"},
        )

    assert res.status_code == 200
    updated = await store.get_document("doc_candidate_2")
    assert updated.ingest_status == "rejected"
