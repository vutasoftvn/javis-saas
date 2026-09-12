from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.publisher import publish_skill_spec
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.models import RunRecord
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.skills.candidate_store import InMemorySkillCandidateStore
from agent.skills.contracts import SkillCandidate, SkillSpec, SkillStatus
from agent.skills.improvement_repository import (
    InMemorySkillImprovementRepository,
    SkillUsageObservation,
)
from apps.cosa.api.app import create_cosa_app
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from agent_testkit.fake_sdk_model import FakeSDKModel


async def _get_app_client(monkeypatch):
    monkeypatch.setenv("COSA_SKILL_IMPROVEMENT_MODE", "CANDIDATE")
    repo = InMemoryRunRepository()
    spec_reg = InMemorySpecRegistryRepository()
    cand_store = InMemorySkillCandidateStore()
    imp_repo = InMemorySkillImprovementRepository(candidate_store=cand_store)

    plane = build_cosa_agent_plane(
        repository=repo,
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=spec_reg,
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
        skill_candidate_store=cand_store,
        skill_improvement_repository=imp_repo,
    )

    app = create_cosa_app(plane=plane)
    app.state.cosa_plane = plane
    app.state.skill_candidate_store = cand_store
    app.state.skill_improvement_repository = imp_repo

    override_authenticated_identity(
        app,
        principal_id="user:tester",
        platform_user_id="u1",
        workspace_id="ws_fb",
    )

    client = TestClient(app)
    return {
        "client": client,
        "plane": plane,
        "repo": repo,
        "spec_reg": spec_reg,
        "cand_store": cand_store,
        "imp_repo": imp_repo,
    }


@pytest.mark.asyncio
async def test_feedback_requires_idempotency_key_and_a_real_observed_run(monkeypatch) -> None:
    data = await _get_app_client(monkeypatch)
    client: TestClient = data["client"]
    imp_repo: InMemorySkillImprovementRepository = data["imp_repo"]

    # 1. Missing Idempotency-Key
    res = client.post(
        "/agent/skills/brief_writer/feedback",
        json={"run_id": "run-observed", "success": False, "rating": 1},
    )
    assert res.status_code == 400
    assert "Idempotency-Key" in res.json()["detail"]

    # 2. Missing run_id
    res = client.post(
        "/agent/skills/brief_writer/feedback",
        headers={"Idempotency-Key": "fb-0"},
        json={"success": False, "rating": 1},
    )
    assert res.status_code == 400
    assert "run_id" in res.json()["detail"]

    # 3. Unobserved run
    res = client.post(
        "/agent/skills/brief_writer/feedback",
        headers={"Idempotency-Key": "fb-1"},
        json={"run_id": "run-unobserved", "success": False, "rating": 1},
    )
    assert res.status_code == 400
    assert "No observation found" in res.json()["detail"]

    # 4. Now record valid observation in repo
    obs = SkillUsageObservation(
        workspace_id="ws_fb",
        run_id="run-observed",
        skill_id="brief_writer",
        skill_version="1.0.0",
        definition_hash="hash_bw_1",
        root_spec_id="agent_1",
        root_definition_hash="root_h",
    )
    await imp_repo.record_resolved_skill_use(obs)

    # Allowlist this identity in policy
    monkeypatch.setenv(
        "COSA_SKILL_IMPROVEMENT_ALLOWLIST",
        '[{"skill_id": "brief_writer", "version": "1.0.0", "definition_hash": "hash_bw_1"}]',
    )

    res = client.post(
        "/agent/skills/brief_writer/feedback",
        headers={"Idempotency-Key": "fb-2"},
        json={"run_id": "run-observed", "success": False, "rating": 1},
    )
    assert res.status_code == 200
    resp_data = res.json()["data"]
    assert resp_data["skill_id"] == "brief_writer"
    assert resp_data["improvement_disposition"] == "INSUFFICIENT_SAMPLES"
    assert resp_data["feedback_health"] == "INSUFFICIENT_SAMPLES"


@pytest.mark.asyncio
async def test_low_feedback_never_overwrites_evaluator_score(monkeypatch) -> None:
    data = await _get_app_client(monkeypatch)
    client: TestClient = data["client"]
    cand_store: InMemorySkillCandidateStore = data["cand_store"]
    imp_repo: InMemorySkillImprovementRepository = data["imp_repo"]

    # Seed candidate with known eval_score
    skill = SkillSpec(id="brief_writer", version="1.0.0", instructions="instructions")
    candidate = SkillCandidate(
        candidate_id="cand_test_eval",
        parent_run_id="parent_run",
        proposed_skill=skill,
        eval_score=0.91,
        status=SkillStatus.EVALUATED,
    )
    await cand_store.save_candidate("ws_fb", candidate)

    # Seed observation
    obs = SkillUsageObservation(
        workspace_id="ws_fb",
        run_id="run-observed-2",
        skill_id="brief_writer",
        skill_version="1.0.0",
        definition_hash="hash_bw_1",
        root_spec_id="agent_1",
        root_definition_hash="root_h",
    )
    await imp_repo.record_resolved_skill_use(obs)

    # Submit negative feedback
    res = client.post(
        "/agent/skills/brief_writer/feedback",
        headers={"Idempotency-Key": "fb-low-1"},
        json={"run_id": "run-observed-2", "success": False, "rating": 1},
    )
    assert res.status_code == 200

    saved_cand = await cand_store.get_candidate("ws_fb", "cand_test_eval")
    assert saved_cand is not None
    # Crucial invariant: eval_score must NOT be overwritten!
    assert saved_cand.eval_score == 0.91


@pytest.mark.asyncio
async def test_feedback_idempotent_replay(monkeypatch) -> None:
    data = await _get_app_client(monkeypatch)
    client: TestClient = data["client"]
    imp_repo: InMemorySkillImprovementRepository = data["imp_repo"]

    obs = SkillUsageObservation(
        workspace_id="ws_fb",
        run_id="run-observed-3",
        skill_id="brief_writer",
        skill_version="1.0.0",
        definition_hash="hash_bw_1",
        root_spec_id="agent_1",
        root_definition_hash="root_h",
    )
    await imp_repo.record_resolved_skill_use(obs)

    res1 = client.post(
        "/agent/skills/brief_writer/feedback",
        headers={"Idempotency-Key": "fb-replay"},
        json={"run_id": "run-observed-3", "success": True, "rating": 5},
    )
    assert res1.status_code == 200

    res2 = client.post(
        "/agent/skills/brief_writer/feedback",
        headers={"Idempotency-Key": "fb-replay"},
        json={"run_id": "run-observed-3", "success": True, "rating": 5},
    )
    assert res2.status_code == 200
    assert res1.json()["data"]["feedback_id"] == res2.json()["data"]["feedback_id"]
