"""`agent.consult` — Co-Founder hỏi agent chuyên môn qua child run chỉ đọc."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agent.contracts.run import RunStatus
from agent.governance.contracts import PolicyOutcome

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.consult import CONSULTABLE_PROFILES, create_agent_consult_handler
from apps.cosa.policies.evaluator import READ_ONLY_RUN_KEY, CosaPolicyEngine

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _patch_resolve_spec(monkeypatch):
    async def _fake_resolve_spec(plane, *, run_id, local_spec):
        return local_spec

    monkeypatch.setattr("apps.cosa.worker.run_core.resolve_spec", _fake_resolve_spec)


def _plane(result):
    kernel = AsyncMock()
    kernel.run.return_value = result
    resolver = AsyncMock()
    resolver.resolve_for_run.return_value = {"_company_delegation_token": "jwt"}
    return SimpleNamespace(kernel=kernel, compliance_resolver=resolver)


_CTX = {
    "workspace_id": "ws1",
    "project_id": "proj1",
    "principal": "user:1",
    "correlation_id": "corr_parent",
    "locale": "vi-VN",
}


async def test_consult_runs_target_agent_as_read_only_child_run_in_project_scope():
    plane = _plane(
        SimpleNamespace(
            status=RunStatus.COMPLETED,
            final_output={"response": "Runway 6 tháng, nên cắt 20% chi phí."},
            errors=[],
        )
    )
    handler = create_agent_consult_handler(plane)

    res = await handler({"agent_profile": "finance", "question": "Runway còn bao lâu?"}, _CTX)

    assert res["status"] == "completed"
    assert "Runway 6 tháng" in res["answer"]
    req, spec = plane.kernel.run.await_args.args
    assert spec is AGENT_PROFILE_SPECS["finance"]  # quyền của agent ĐÍCH
    assert req.run_id == res["run_id"] and req.run_id.startswith("consult_")
    assert req.metadata[READ_ONLY_RUN_KEY] is True
    assert req.metadata["consult_depth"] == 1
    assert req.metadata["project_id"] == "proj1"
    assert req.input["prompt"] == "Runway còn bao lâu?"
    # compliance mint delegation theo spec đích, không dùng token của run cha
    assert plane.compliance_resolver.resolve_for_run.await_args.args[1] is spec


@pytest.mark.parametrize(
    ("payload", "ctx", "match"),
    [
        (
            {"agent_profile": "finance", "question": "Runway?? ok"},
            {**_CTX, "consult_depth": 1},
            "nested",
        ),
        (
            {"agent_profile": "finance", "question": "Runway?? ok"},
            {**_CTX, "project_id": None},
            "project_id",
        ),
        ({"agent_profile": "founder_assistant", "question": "tự hỏi mình"}, _CTX, "agent_profile"),
        ({"agent_profile": "cfo", "question": "executive không hỏi được"}, _CTX, "agent_profile"),
    ],
)
async def test_consult_fails_closed(payload, ctx, match):
    plane = _plane(None)
    with pytest.raises(ValueError, match=match):
        await create_agent_consult_handler(plane)(payload, ctx)
    plane.kernel.run.assert_not_awaited()


async def test_consultable_profiles_exclude_cofounder_and_have_specs():
    assert "founder_assistant" not in CONSULTABLE_PROFILES
    assert {"finance", "marketing", "strategy", "sales", "legal"} <= set(CONSULTABLE_PROFILES)
    for p in CONSULTABLE_PROFILES:
        assert p in AGENT_PROFILE_SPECS
        # agent đích không được tự consult tiếp (sâu tối đa 1 cấp)
        assert "agent.consult" not in AGENT_PROFILE_SPECS[p].capability_refs


async def test_read_only_run_denies_writes_but_allows_reads():
    engine = CosaPolicyEngine()
    ctx = {READ_ONLY_RUN_KEY: True}
    assert engine.evaluate("finance.transaction.record", {}, ctx).outcome == PolicyOutcome.DENY
    assert engine.evaluate("commercial.campaign_asset.write", {}, ctx).outcome == PolicyOutcome.DENY
    assert engine.evaluate("operations.task.list", {}, ctx).outcome == PolicyOutcome.ALLOW
    assert engine.evaluate("finance.transaction.record", {}, {}).outcome != PolicyOutcome.DENY


async def test_capability_registered_on_built_plane():
    from agent.conversations.repository import InMemoryConversationRepository
    from agent.coordination.scheduler import RunScheduler
    from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
    from agent.registry.repository import InMemorySpecRegistryRepository
    from agent.runs.leases import RunLeaseManager
    from agent.runs.repository import InMemoryRunRepository
    from agent.runs.stream_events import InMemoryRunStreamEventRepository
    from agent_testkit.fake_sdk_model import FakeSDKModel

    from apps.cosa.capabilities.client import CompanyServiceClient
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    plane = build_cosa_agent_plane(
        company_client=AsyncMock(spec=CompanyServiceClient),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
    reg = plane.capability_registry.get("agent.consult")
    assert reg is not None
