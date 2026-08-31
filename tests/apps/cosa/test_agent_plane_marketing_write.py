from __future__ import annotations

from unittest.mock import AsyncMock
import pytest

from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane


@pytest.fixture
def mock_company_client():
    client = AsyncMock(spec=CompanyServiceClient)
    client.get.return_value = {}
    client.patch.return_value = {"id": "ctx-100", "revision": 3, "status": "approved"}
    client.post.return_value = {}
    return client


@pytest.fixture
def plane(mock_company_client):
    return build_cosa_agent_plane(
        company_client=mock_company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )


@pytest.mark.asyncio
async def test_marketing_context_write_capability(plane, mock_company_client):
    """Verify commercial.marketing_context.write contract, approval policy, and execution."""
    reg = plane.capability_registry.get("commercial.marketing_context.write")
    assert reg is not None
    assert reg.spec.risk == CapabilityRisk.MEDIUM
    assert reg.spec.approval_policy == ApprovalPolicy.ALWAYS

    handler = reg.handler
    payload = {
        "workspace_id": "ws-write-1",
        "expected_revision": 2,
        "product_marketing": {
            "category": "Enterprise AI SaaS",
            "positioningStatement": "Updated positioning statement for enterprise buyers.",
        },
        "change_reason": "Quarterly market positioning refinement",
    }
    res = await handler(payload, {"workspace_id": "ws-write-1"})

    assert res["status"] == "approved"
    assert res["revision"] == 3
    mock_company_client.patch.assert_awaited_once_with(
        "/commercial/marketing-context?workspace_id=ws-write-1",
        json={
            "workspaceId": "ws-write-1",
            "expectedRevision": 2,
            "productMarketing": {
                "category": "Enterprise AI SaaS",
                "positioningStatement": "Updated positioning statement for enterprise buyers.",
            },
            "changeReason": "Quarterly market positioning refinement",
        },
        headers={"X-Workspace-Id": "ws-write-1"},
    )


@pytest.mark.asyncio
async def test_marketing_context_write_requires_expected_revision(plane):
    """Verify commercial.marketing_context.write fails if expected_revision is omitted."""
    reg = plane.capability_registry.get("commercial.marketing_context.write")
    handler = reg.handler

    with pytest.raises(ValueError) as exc_info:
        await handler({"workspace_id": "ws-write-1"}, {"workspace_id": "ws-write-1"})
    assert "expected_revision" in str(exc_info.value)


@pytest.mark.asyncio
async def test_campaign_asset_write_capability(plane):
    """Verify commercial.campaign_asset.write saves campaign asset with artifact reference."""
    reg = plane.capability_registry.get("commercial.campaign_asset.write")
    assert reg is not None
    assert reg.spec.risk == CapabilityRisk.LOW

    handler = reg.handler
    res = await handler(
        {
            "workspace_id": "ws-write-1",
            "asset_name": "Q3 Cold Outbound Sequence",
            "asset_type": "email_sequence",
            "content": "# Cold Outbound Sequence\n\nEmail 1: Intro...",
        },
        {"workspace_id": "ws-write-1"},
    )

    assert res["status"] == "saved"
    assert res["asset_id"].startswith("asset_")
    assert res["object_ref"].startswith("artifact://ws-write-1/campaign-assets/")


@pytest.mark.asyncio
async def test_experiment_write_capability(plane):
    """Verify commercial.experiment.write creates experiment in pending_approval status."""
    reg = plane.capability_registry.get("commercial.experiment.write")
    assert reg is not None
    assert reg.spec.risk == CapabilityRisk.MEDIUM
    assert reg.spec.approval_policy == ApprovalPolicy.ALWAYS

    handler = reg.handler
    res = await handler(
        {
            "workspace_id": "ws-write-1",
            "hypothesis": "Short subject lines increase open rate by 20%",
            "metric": "open_rate",
            "target_value": 0.35,
            "metric_contract_id": "contract-open-rate-001",
        },
        {"workspace_id": "ws-write-1"},
    )

    assert res["status"] == "pending_approval"
    assert res["experiment_id"].startswith("exp_")
    assert res["hypothesis"] == "Short subject lines increase open rate by 20%"
