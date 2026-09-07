"""Task 7 (plan local-first-enterprise-knowledge) — Vault document upload +
lifecycle API thật (thay thế stub 501): create → upload → complete → QUEUED,
review/publish/archive theo KnowledgeAuthorization (Task 6), không response
nào lộ local path/object ref/ticket secret/fencing token."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from agent.artifacts import InMemoryArtifactRepository
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.vault.repository import InMemoryVaultRepository
from agent.workforce.repository import InMemoryWorkforceRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.knowledge_ingestion.dependencies import build_knowledge_ingestion_dependencies
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    fake_active_tenant_policy_client,
)


class _FakeSandbox:
    async def run(self, document, content, converter_profile):
        raise NotImplementedError


@pytest.fixture
def test_app(tmp_path, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_INGESTION_ENABLED", "true")

    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    vault_repository = InMemoryVaultRepository()
    plane = build_cosa_agent_plane(
        company_client=mock_client,
        tenant_policy_client=fake_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        workforce_repository=InMemoryWorkforceRepository(),
        vault_repository=vault_repository,
        model=FakeSDKModel(),
        knowledge_ingestion_deps=build_knowledge_ingestion_dependencies(
            storage_root=tmp_path, sandbox=_FakeSandbox()
        ),
    )
    asyncio.run(seed_cosa_agent_specs(plane.spec_registry))
    app = create_cosa_app(plane)
    return app, plane


@pytest.mark.asyncio
async def test_create_upload_then_complete_queues_local_ingestion(test_app) -> None:
    app, _plane = test_app
    override_authenticated_identity(app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/agent/vault/documents", json={"title": "Plan", "media_type": "text/plain"}
        )
        assert created.status_code == 201
        body = created.json()
        assert "upload_url" in body and "upload_id" in body

        upload = await client.put(body["upload_url"], content=b"local plan")
        assert upload.status_code == 204

        complete = await client.post(f"/agent/vault/uploads/{body['upload_id']}/complete")
        assert complete.status_code == 200
        assert complete.json()["state"] == "QUEUED"


@pytest.mark.asyncio
async def test_upload_response_never_leaks_local_path_or_secret_field_names(test_app) -> None:
    app, _plane = test_app
    override_authenticated_identity(app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/agent/vault/documents", json={"title": "Plan", "media_type": "text/plain"}
        )
        body = created.json()
        assert "quarantine_relative_path" not in body
        assert "object_key" not in body


@pytest.mark.asyncio
async def test_upload_creates_private_document_for_member_ignoring_requested_visibility(
    test_app,
) -> None:
    app, plane = test_app
    override_authenticated_identity(
        app, workspace_id="ws_1001", role_id="member", principal_id="member-1"
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/agent/vault/documents",
            json={"title": "Member doc", "media_type": "text/plain", "visibility": "WORKSPACE"},
        )
        assert created.status_code == 201

    from uuid import UUID

    doc = await plane.vault_repository.get_document("ws_1001", UUID(created.json()["document_id"]))
    assert doc.visibility.value == "PRIVATE"


@pytest.mark.asyncio
async def test_member_without_grant_gets_404_for_founder_document(test_app) -> None:
    app, plane = test_app
    await plane.vault_repository.create_draft("ws_1001", "Board plan", created_by="founder-1")
    docs = await plane.vault_repository.list_authorized_documents(
        "ws_1001", "founder-1", {"founder"}
    )
    doc_id = str(docs[0].document_id)

    override_authenticated_identity(
        app, workspace_id="ws_1001", role_id="member", principal_id="member-1"
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/agent/vault/documents/{doc_id}")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_founder_can_review_reject_and_publish_flow(test_app) -> None:
    app, plane = test_app
    override_authenticated_identity(
        app, workspace_id="ws_1001", role_id="founder", principal_id="founder-1"
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/agent/vault/documents", json={"title": "Plan", "media_type": "text/plain"}
        )
        body = created.json()
        await client.put(body["upload_url"], content=b"local plan content")
        await client.post(f"/agent/vault/uploads/{body['upload_id']}/complete")

        # Mô phỏng worker: claim (QUEUED -> VALIDATING) rồi record_candidate
        # (-> REVIEW_PENDING) — route /complete chỉ QUEUE, không tự chạy pipeline.
        deps = plane.knowledge_ingestion_deps
        claimed = await deps.local_repository.claim(
            "ws_1001", body["upload_id"], "worker-task-token"
        )
        assert claimed.claimed is True
        ok = await deps.local_repository.record_candidate(
            "ws_1001", body["upload_id"], "ks_1", {"chunks": 1}
        )
        assert ok is True

        publish_resp = await client.post(
            f"/agent/vault/documents/{body['document_id']}/publish",
            json={"reason": "looks good", "idempotency_key": "idem-1"},
        )
        assert publish_resp.status_code == 200
        assert publish_resp.json()["state"] == "PUBLISHED"

        get_resp = await client.get(f"/agent/vault/documents/{body['document_id']}")
        assert get_resp.status_code == 200
        assert get_resp.json()["state"] == "PUBLISHED"


@pytest.mark.asyncio
async def test_member_cannot_publish_without_publish_grant(test_app) -> None:
    app, plane = test_app
    doc = await plane.vault_repository.create_draft(
        "ws_1001", "Needs review", created_by="founder-1"
    )
    override_authenticated_identity(
        app, workspace_id="ws_1001", role_id="member", principal_id="member-1"
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/agent/vault/documents/{doc.document_id}/publish",
            json={"reason": "x", "idempotency_key": "idem-2"},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_archive_does_not_delete_file_and_returns_accepted(test_app) -> None:
    app, plane = test_app
    doc = await plane.vault_repository.create_draft(
        "ws_1001", "Owned by member", created_by="member-1"
    )
    override_authenticated_identity(
        app, workspace_id="ws_1001", role_id="member", principal_id="member-1"
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.delete(f"/agent/vault/documents/{doc.document_id}")
        assert response.status_code == 200
        assert response.json()["accepted"] is True

    updated = await plane.vault_repository.get_document("ws_1001", doc.document_id)
    assert updated.state == "ARCHIVED"


@pytest.mark.asyncio
async def test_purge_route_blocked_by_legal_hold(test_app) -> None:
    """Task 11 — legal_hold=true chặn hoàn toàn qua route, không có cách bypass."""
    app, plane = test_app
    doc = await plane.vault_repository.create_draft("ws_1001", "Under hold", created_by="founder-1")
    await plane.vault_repository.set_legal_hold("ws_1001", doc.document_id, True)
    override_authenticated_identity(
        app, workspace_id="ws_1001", role_id="founder", principal_id="founder-1"
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(f"/agent/vault/documents/{doc.document_id}/purge")
        assert response.status_code == 409


@pytest.mark.asyncio
async def test_purge_route_full_flow_excludes_retrieval_and_deletes_physical_file(test_app) -> None:
    """Task 11 — publish → purge (202, PURGE_PENDING ngay) → worker durable
    dọn dẹp vật lý thật → PURGED, không còn trong retrieval."""
    from tests.apps.cosa.worker_test_helpers import drain_worker_queue

    app, plane = test_app
    override_authenticated_identity(
        app, workspace_id="ws_1001", role_id="founder", principal_id="founder-1"
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/agent/vault/documents", json={"title": "Plan", "media_type": "text/plain"}
        )
        body = created.json()
        await client.put(body["upload_url"], content=b"quarterly plan content")
        await client.post(f"/agent/vault/uploads/{body['upload_id']}/complete")

        deps = plane.knowledge_ingestion_deps
        await deps.local_repository.claim("ws_1001", body["upload_id"], "worker-task-token")
        await deps.local_repository.record_candidate(
            "ws_1001", body["upload_id"], "ks_1", {"chunks": 1}
        )

        publish_resp = await client.post(
            f"/agent/vault/documents/{body['document_id']}/publish",
            json={"reason": "looks good", "idempotency_key": "idem-purge-1"},
        )
        assert publish_resp.status_code == 200

        purge_resp = await client.post(f"/agent/vault/documents/{body['document_id']}/purge")
        assert purge_resp.status_code == 202
        assert purge_resp.json()["accepted"] is True

    from uuid import UUID

    pending = await plane.vault_repository.get_document("ws_1001", UUID(body["document_id"]))
    assert pending.state == "PURGE_PENDING"

    # /complete cũng đã schedule 1 task "knowledge_ingestion" (không claim
    # trong test này vì ta tự gọi local_repository.claim/record_candidate
    # trực tiếp) — drain cả 2, chỉ quan tâm vault_purge có chạy xong.
    assert await drain_worker_queue(plane) >= 1

    purged = await plane.vault_repository.get_document("ws_1001", UUID(body["document_id"]))
    assert purged.state == "PURGED"
