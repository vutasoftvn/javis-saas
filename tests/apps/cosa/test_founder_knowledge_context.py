"""Task 10 (plan local-first-enterprise-knowledge) — chat run thật (qua
worker durable, không gọi thẳng hàm Python) phải tới được
`workspace.context.read` qua đúng gateway/capability path, và context trả về
cho model vẫn bị lọc theo role_id của principal đang chạy — kể cả khi
capability này chạy trong kernel, không phải HTTP route."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.vault.models import VaultClassification, VaultVisibility
from agent.vault.repository import InMemoryVaultRepository
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response, tool_call_response

from apps.cosa.agents.seed import seed_cosa_runtime_specs
from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    fake_active_tenant_policy_client,
)
from tests.apps.cosa.worker_test_helpers import drain_worker_queue

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def test_app():
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
        vault_repository=vault_repository,
        model=FakeSDKModel(
            responses=[
                tool_call_response(
                    "call_workspace_ctx",
                    "workspace.context.read",
                    arguments='{"operation_id": "enterpriseKnowledgeSearch", "variables": {"query": "lương"}}',
                ),
                text_response("Đã kiểm tra context workspace."),
            ]
        ),
    )
    asyncio.run(
        seed_cosa_runtime_specs(
            spec_registry=plane.spec_registry,
            capability_registry=plane.capability_registry,
            skillpacks_root=REPO_ROOT / "skillpacks",
        )
    )
    app = create_cosa_app(plane=plane)
    return app, plane


async def _seed_restricted_doc(plane, workspace_id: str, *, created_by: str, content: str) -> None:
    vault_doc = await plane.vault_repository.create_draft(
        workspace_id,
        "board handbook",
        created_by=created_by,
        classification=VaultClassification.INTERNAL,
        visibility=VaultVisibility.PRIVATE,
    )
    version = await plane.vault_repository.append_version(
        workspace_id,
        vault_doc.document_id,
        object_ref={"path": "handbook.md"},
        checksum_sha256="0" * 64,
        size_bytes=len(content),
        source_uri=f"vault://{vault_doc.document_id}",
        created_by=created_by,
    )
    await plane.vault_repository.update_document_state(
        workspace_id, vault_doc.document_id, "PUBLISHED"
    )

    from agent.knowledge.models import KnowledgeChunk, KnowledgeDocument

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    doc = KnowledgeDocument(
        id=doc_id,
        workspace_id=workspace_id,
        title="board handbook",
        ingest_status="published",
        vault_document_id=str(vault_doc.document_id),
        vault_version_id=str(version.version_id),
        access_policy_version=1,
        chunks=[
            KnowledgeChunk(
                id=f"chk_{doc_id}_0",
                document_id=doc_id,
                workspace_id=workspace_id,
                chunk_index=0,
                content=content,
            )
        ],
    )
    await plane.knowledge_ingestion_service.ingest_normalized_document(doc)


@pytest.mark.asyncio
async def test_founder_assistant_can_request_workspace_knowledge_via_gateway(test_app):
    """founder_assistant KHÔNG phải 1 agent profile riêng (không tạo mới —
    CLAUDE.md rule 3) — đây chính là spec Operations mặc định cho chat, giờ
    đã có capability_ref workspace.context.read (Task 10)."""
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    app, plane = test_app
    await _seed_restricted_doc(
        plane, workspace_id, created_by="user:founder_owner", content="lương ban điều hành quý này"
    )
    override_authenticated_identity(
        app, workspace_id=workspace_id, role_id="founder", principal_id="user:founder_owner"
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res_conv = await ac.post("/agent/conversations", json={"title": "Kế hoạch quý"})
        assert res_conv.status_code == 201
        conv_id = res_conv.json()["id"]

        res_msg = await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={
                "content": "Tóm tắt kế hoạch quý",
                "data_access": {"categories": ["NON_PERSONAL"]},
            },
        )
        assert res_msg.status_code == 202
        run_id = res_msg.json()["run_id"]

        assert await drain_worker_queue(plane) == 1

    tool_calls = await plane.repository.list_tool_calls(run_id)
    matching = [tc for tc in tool_calls if tc.capability_id == "workspace.context.read"]
    assert matching, "workspace.context.read phải được gateway ghi nhận đã gọi"
    assert matching[0].status == "completed"
    citations = matching[0].output_payload["citations"]
    assert citations
    assert "lương" in citations[0]["snippet"]


@pytest.mark.asyncio
async def test_member_run_context_excludes_denied_citation(test_app):
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    app, plane = test_app
    await _seed_restricted_doc(
        plane, workspace_id, created_by="user:founder_owner", content="lương ban điều hành quý này"
    )
    override_authenticated_identity(
        app, workspace_id=workspace_id, role_id="member", principal_id="user:member_x"
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res_conv = await ac.post("/agent/conversations", json={"title": "Lương ban điều hành"})
        assert res_conv.status_code == 201
        conv_id = res_conv.json()["id"]

        res_msg = await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={
                "content": "Lương ban điều hành",
                "data_access": {"categories": ["NON_PERSONAL"]},
            },
        )
        assert res_msg.status_code == 202
        run_id = res_msg.json()["run_id"]

        assert await drain_worker_queue(plane) == 1

    tool_calls = await plane.repository.list_tool_calls(run_id)
    matching = [tc for tc in tool_calls if tc.capability_id == "workspace.context.read"]
    assert matching
    citations = matching[0].output_payload["citations"]
    assert citations == []
    assert "lương ban điều hành" not in str(matching[0].output_payload)
