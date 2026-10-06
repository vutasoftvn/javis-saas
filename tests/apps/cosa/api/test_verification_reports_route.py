from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.skills.candidate_store import InMemorySkillCandidateStore
from agent.verification.repository import (
    InMemoryVerificationReportRepository,
    VerificationReport,
)
from agent.workforce.repository import InMemoryWorkforceRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from fastapi.testclient import TestClient

from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity

_URL = "/agent/workforce/verification-reports"


def _report(**over):
    base = dict(
        report_id="vr_1",
        workspace_id="ws-test",
        task_id="t1",
        run_id="run_1",
        verifier_run_id="vrun_1",
        verdict="FAIL",
        mode="deterministic",
        criteria_results=[
            {
                "id": "c1",
                "required": True,
                "check": "deterministic",
                "verdict": "fail",
                "reason": "artifact_not_found",
                "extra_internal": "x",
            }
        ],
        criteria_hash="HASH_C",
        output_hash="HASH_O",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    base.update(over)
    return VerificationReport(**base)


@pytest.fixture
def env():
    repo = InMemoryVerificationReportRepository()
    plane = build_cosa_agent_plane(
        company_client=AsyncMock(spec=CompanyServiceClient),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
        workforce_repository=InMemoryWorkforceRepository(),
        skill_candidate_store=InMemorySkillCandidateStore(),
    )
    plane.verification_report_repository = repo
    app = create_cosa_app(plane=plane)
    override_authenticated_identity(app, workspace_id="ws-test")
    return {"app": app, "client": TestClient(app), "repo": repo, "plane": plane}


def test_unauthenticated_is_rejected():
    plane = build_cosa_agent_plane(
        company_client=AsyncMock(spec=CompanyServiceClient),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
        workforce_repository=InMemoryWorkforceRepository(),
        skill_candidate_store=InMemorySkillCandidateStore(),
    )
    client = TestClient(create_cosa_app(plane=plane))
    assert client.get(_URL, params={"taskId": "t1"}).status_code in (401, 403)


@pytest.mark.asyncio
async def test_scoped_to_workspace_and_shape_hides_hashes(env):
    await env["repo"].create_if_absent(_report())
    await env["repo"].create_if_absent(
        _report(report_id="vr_o", run_id="run_o", workspace_id="ws-other")
    )
    resp = env["client"].get(_URL, params={"taskId": "t1", "workspaceId": "ws-other"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert [d["reportId"] for d in data] == ["vr_1"]
    assert data[0] == {
        "reportId": "vr_1",
        "taskId": "t1",
        "runId": "run_1",
        "verifierRunId": "vrun_1",
        "verdict": "FAIL",
        "mode": "deterministic",
        "criteriaResults": [
            {
                "id": "c1",
                "required": True,
                "check": "deterministic",
                "verdict": "fail",
                "reason": "artifact_not_found",
            }
        ],
        "createdAt": "2026-01-01T12:00:00Z",
    }
    assert "HASH_C" not in resp.text and "HASH_O" not in resp.text


@pytest.mark.asyncio
async def test_run_id_returns_single_report_and_never_other_workspace(env):
    await env["repo"].create_if_absent(_report())
    await env["repo"].create_if_absent(
        _report(report_id="vr_o", run_id="run_o", workspace_id="ws-other")
    )
    ok = env["client"].get(_URL, params={"runId": "run_1"}).json()["data"]
    assert [d["reportId"] for d in ok] == ["vr_1"]
    assert env["client"].get(_URL, params={"runId": "run_o"}).json()["data"] == []


def test_missing_task_and_run_is_422(env):
    assert env["client"].get(_URL).status_code == 422


@pytest.mark.asyncio
async def test_limit_is_clamped(env):
    for i in range(60):
        await env["repo"].create_if_absent(
            _report(
                report_id=f"vr_{i:02d}",
                run_id=f"r{i}",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
    client = env["client"]
    assert len(client.get(_URL, params={"taskId": "t1", "limit": 500}).json()["data"]) == 50
    assert len(client.get(_URL, params={"taskId": "t1", "limit": 0}).json()["data"]) == 1
    assert len(client.get(_URL, params={"taskId": "t1"}).json()["data"]) == 20


def test_empty_repository_and_missing_repository(env):
    assert env["client"].get(_URL, params={"taskId": "t1"}).json()["data"] == []
    env["plane"].verification_report_repository = None
    resp = env["client"].get(_URL, params={"taskId": "t1"})
    assert resp.status_code == 200 and resp.json()["data"] == []


def test_non_integer_limit_is_422(env):
    assert env["client"].get(_URL, params={"taskId": "t1", "limit": "abc"}).status_code == 422


def test_over_long_ids_are_422(env):
    assert env["client"].get(_URL, params={"taskId": "t" * 129}).status_code == 422
    assert env["client"].get(_URL, params={"runId": "r" * 129}).status_code == 422
    assert env["client"].get(_URL, params={"taskId": "t" * 128}).status_code == 200


@pytest.mark.asyncio
async def test_task_and_run_mismatch_returns_empty(env):
    await env["repo"].create_if_absent(_report())
    resp = env["client"].get(_URL, params={"taskId": "other_task", "runId": "run_1"})
    assert resp.status_code == 200 and resp.json()["data"] == []
    ok = env["client"].get(_URL, params={"taskId": "t1", "runId": "run_1"}).json()["data"]
    assert [d["reportId"] for d in ok] == ["vr_1"]
