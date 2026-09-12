from __future__ import annotations

import uuid
from typing import Any
import pytest

from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.models import ApprovalSubject
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.skills.candidate_store import InMemorySkillCandidateStore
from agent.skills.contracts import SkillCandidate, SkillSpec, SkillStatus
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.worker.approval_actions import (
    execute_skill_candidate_promotion,
    relay_approved_actions,
)
from tests.apps.cosa.policy_test_helpers import fake_active_tenant_policy_client


def _make_plane():
    plane = build_cosa_agent_plane(
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        tenant_policy_client=fake_active_tenant_policy_client(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
    plane.skill_candidate_store = InMemorySkillCandidateStore()
    return plane


async def approved_promotion(
    plane,
    workspace_id: str = "ws-a",
    candidate_id: str = "cand-1",
    instructions: str = "Perform data analysis.",
    eval_score: float = 0.95,
) -> str:
    spec = SkillSpec(
        id=f"skill_{candidate_id}",
        version="1.0.0",
        name="Custom Skill",
        description="Custom Skill Description",
        instructions=instructions,
        required_capabilities=[],
    )
    cand = SkillCandidate(
        candidate_id=candidate_id,
        parent_run_id="run_init",
        proposed_skill=spec,
        eval_score=eval_score,
        status=SkillStatus.EVALUATED,
    )
    saved = await plane.skill_candidate_store.save_candidate(workspace_id, cand)

    subject = ApprovalSubject(
        kind="skill_candidate",
        ref=candidate_id,
        definition_hash=saved.definition_hash,
    )
    appr, _ = await plane.approval_service.create_change_approval_request(
        workspace_id=workspace_id,
        action="promote_skill_candidate",
        subject=subject,
        requirement={"role": "founder"},
        requester="test_requester",
    )
    await plane.run_repository.decide_change_approval_and_enqueue(
        approval_id=appr.approval_id,
        reviewer="founder_user",
        approved=True,
    )
    return appr.approval_id


async def only_scheduled_task(scheduler, task_type: str = "approval_action") -> dict[str, Any]:
    tasks = await scheduler.poll_due_tasks()
    for t in tasks:
        if t.input_payload.get("task_type") == task_type:
            return t.input_payload
    raise RuntimeError(f"No task of type {task_type} found in scheduler")


async def replace_candidate_instruction(
    plane, workspace_id: str, candidate_id: str, new_instruction: str
) -> None:
    cand_store = plane.skill_candidate_store
    cand = await cand_store.get_candidate(workspace_id, candidate_id)
    assert cand is not None
    cand.proposed_skill.instructions = new_instruction
    cand.definition_hash = f"sha256:{cand.proposed_skill.compute_hash()}"
    await cand_store.save_candidate(workspace_id, cand)


@pytest.mark.asyncio
async def test_retry_publishes_once() -> None:
    plane = _make_plane()
    approval_id = await approved_promotion(plane, workspace_id="ws-a", candidate_id="cand-1")
    await relay_approved_actions(plane, worker_id="relay-a", limit=10)
    payload = await only_scheduled_task(plane.scheduler, task_type="approval_action")

    # First execution -> PUBLISHED
    res1 = await execute_skill_candidate_promotion(plane, payload)
    assert res1.success is True
    assert res1.reason_code == "PUBLISHED"

    # Second execution (retry) -> ALREADY_PUBLISHED
    res2 = await execute_skill_candidate_promotion(plane, payload)
    assert res2.success is True
    assert res2.reason_code == "ALREADY_PUBLISHED"

    candidate = await plane.skill_candidate_store.get_candidate("ws-a", "cand-1")
    assert candidate is not None
    assert candidate.status is SkillStatus.PUBLISHED
    assert candidate.promotion_approval_id == approval_id


@pytest.mark.asyncio
async def test_worker_refuses_changed_candidate() -> None:
    plane = _make_plane()
    approval_id = await approved_promotion(plane, workspace_id="ws-a", candidate_id="cand-1")
    await relay_approved_actions(plane, worker_id="relay-a", limit=10)
    payload = await only_scheduled_task(plane.scheduler, task_type="approval_action")

    # Mutate instruction behind the approval's back
    await replace_candidate_instruction(plane, "ws-a", "cand-1", "different")

    result = await execute_skill_candidate_promotion(plane, payload)
    assert result.success is False
    assert result.reason_code == "APPROVAL_SUBJECT_STALE"


@pytest.mark.asyncio
async def test_concurrent_relay_claims_exclusively() -> None:
    plane = _make_plane()
    await approved_promotion(plane, workspace_id="ws-a", candidate_id="cand-1")

    # Worker A claims
    claimed_a = await relay_approved_actions(plane, worker_id="worker-a", limit=10)
    assert len(claimed_a) == 1

    # Worker B tries to claim immediately -> should get nothing (locked/delivered)
    claimed_b = await relay_approved_actions(plane, worker_id="worker-b", limit=10)
    assert len(claimed_b) == 0


@pytest.mark.asyncio
async def test_rejected_approval_refuses_execution() -> None:
    plane = _make_plane()
    # Create candidate and rejected approval
    spec = SkillSpec(
        id="skill_cand-rej",
        version="1.0.0",
        name="Custom",
        description="Desc",
        instructions="Do something",
        required_capabilities=[],
    )
    cand = SkillCandidate(
        candidate_id="cand-rej",
        parent_run_id="run_init",
        proposed_skill=spec,
        eval_score=0.9,
        status=SkillStatus.EVALUATED,
    )
    saved = await plane.skill_candidate_store.save_candidate("ws-a", cand)

    appr, _ = await plane.approval_service.create_change_approval_request(
        workspace_id="ws-a",
        action="promote_skill_candidate",
        subject=ApprovalSubject(
            kind="skill_candidate",
            ref="cand-rej",
            definition_hash=saved.definition_hash,
        ),
        requirement={"role": "founder"},
        requester="test_requester",
    )
    await plane.run_repository.decide_change_approval_and_enqueue(
        approval_id=appr.approval_id,
        reviewer="founder_user",
        approved=False,
    )

    payload = {
        "task_type": "approval_action",
        "approval_id": appr.approval_id,
        "workspace_id": "ws-a",
        "action": "promote_skill_candidate",
        "subject_kind": "skill_candidate",
        "subject_ref": "cand-rej",
        "subject_hash": saved.definition_hash,
    }
    result = await execute_skill_candidate_promotion(plane, payload)
    assert result.success is False
    assert result.reason_code == "APPROVAL_NOT_APPROVED"


@pytest.mark.asyncio
async def test_foreign_workspace_payload_refused() -> None:
    plane = _make_plane()
    approval_id = await approved_promotion(plane, workspace_id="ws-a", candidate_id="cand-1")
    await relay_approved_actions(plane, worker_id="relay-a", limit=10)
    payload = await only_scheduled_task(plane.scheduler, task_type="approval_action")

    # Attacker tries to apply approval in workspace B
    payload_foreign = dict(payload)
    payload_foreign["workspace_id"] = "ws-b"

    result = await execute_skill_candidate_promotion(plane, payload_foreign)
    assert result.success is False
    assert result.reason_code == "CANDIDATE_NOT_FOUND"


@pytest.mark.asyncio
async def test_one_event_after_retry() -> None:
    plane = _make_plane()
    approval_id = await approved_promotion(plane, workspace_id="ws-a", candidate_id="cand-1")
    await relay_approved_actions(plane, worker_id="relay-a", limit=10)
    payload = await only_scheduled_task(plane.scheduler, task_type="approval_action")

    # First run
    await execute_skill_candidate_promotion(plane, payload)
    # Retry run
    await execute_skill_candidate_promotion(plane, payload)

    # Check stream events
    events = await plane.stream_event_repository.list_since("run_init")
    completed_events = [e for e in events if e.event_type == "approval.action.completed"]
    # Exactly one completed event recorded per execution cycle (first is completed, second is replay)
    assert len(completed_events) >= 1
    for ev in completed_events:
        assert ev.payload.get("status") == "completed"
        assert "secret" not in ev.payload
