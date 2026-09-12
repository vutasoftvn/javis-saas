from __future__ import annotations

import uuid
from typing import Any
import pytest

from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.models import PublishedSpecRecord
from agent.registry.publisher import publish_skill_spec
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.skills.candidate_store import InMemorySkillCandidateStore
from agent.skills.contracts import SkillSpec, SkillStatus
from agent.skills.eval_contract import SkillEvalCase, SkillEvalExpected, SkillEvalSuite
from agent.skills.improvement_repository import (
    InMemorySkillImprovementRepository,
    SkillImprovementOutbox,
    SkillImprovementRequest,
)
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.skills.improvement_evaluators import RegisteredSkillEvaluator, SkillEvaluatorRegistry
from apps.cosa.skills.improvement_policy import load_effective_improvement_policy
from apps.cosa.skills.improvement_service import SkillImprovementService
from apps.cosa.worker.main import dispatch_one_task
from apps.cosa.worker.skill_improvement import (
    execute_skill_improvement_task,
    relay_skill_improvement_outbox,
)
from tests.apps.cosa.policy_test_helpers import fake_active_tenant_policy_client


class _MockKernel:
    def __init__(self) -> None:
        self.seen_specs: list[AgentSpec] = []

    async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult:
        self.seen_specs.append(spec)
        content = "Enhanced brief" if "Enhanced" in spec.instructions else "Base brief"
        return RunResult(
            run_id="run_mock_eval",
            status=RunStatus.COMPLETED,
            final_output={"response": content},
        )


async def _make_plane(
    *,
    mode: str = "CANDIDATE",
    allowed_identities: list | None = None,
    with_evaluator: bool = True,
    mutator: Any | None = None,
):
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
    plane.skill_improvement_repository = InMemorySkillImprovementRepository(
        candidate_store=plane.skill_candidate_store
    )

    # Register default test skill
    base_skill = SkillSpec(
        id="brief",
        version="1.0.0",
        instructions="Always write concise bullet points.",
        required_capabilities=[],
    )
    pub_record = await publish_skill_spec(base_skill, repository=plane.spec_registry, publisher="cosa")
    identity = ("brief", "1.0.0", pub_record.definition_hash)
    identities = allowed_identities if allowed_identities is not None else [identity]

    policy = load_effective_improvement_policy(
        mode=mode,
        allowed_identities=identities,
    )

    eval_registry = SkillEvaluatorRegistry()
    if with_evaluator:
        suite = SkillEvalSuite(
            skill_id="brief",
            skill_version="1.0.0",
            cases=(
                SkillEvalCase(
                    id="c1",
                    input={"prompt": "Summarize status"},
                    expected=SkillEvalExpected(outcome="accept", reason="brief"),
                ),
            ),
        )
        eval_registry.register(
            identity,
            RegisteredSkillEvaluator(
                suite=suite,
                suite_ref="brief.eval.yaml",
                custom_score_fn=lambda res, case: 0.95 if "Enhanced" in str(res.final_output) else 0.50,
            ),
        )

    # Test mutator that improves instructions
    def test_mutator(skill_spec):
        mutated = skill_spec.model_copy(
            update={"instructions": f"{skill_spec.instructions} Enhanced."}
        )
        return mutated, "Enhanced instructions"

    chosen_mutator = mutator if mutator is not None else test_mutator
    plane.skill_improvement_service = SkillImprovementService(
        repository=plane.skill_improvement_repository,
        spec_registry=plane.spec_registry,
        candidate_store=plane.skill_candidate_store,
        kernel=_MockKernel(),
        policy=policy,
        evaluator_registry=eval_registry,
        mutator=chosen_mutator,
    )

    return plane, identity


async def _queued_request(
    plane, workspace_id: str = "ws-a", skill_id: str = "brief"
) -> SkillImprovementRequest:
    repo = plane.skill_improvement_repository
    req_id = f"sir_{uuid.uuid4().hex[:12]}"
    rec = await plane.spec_registry.get("skill", skill_id, "1.0.0")
    def_hash = rec.definition_hash if rec else "sha256:default_hash"

    req = SkillImprovementRequest(
        request_id=req_id,
        workspace_id=workspace_id,
        skill_id=skill_id,
        skill_version="1.0.0",
        definition_hash=def_hash,
        trigger="feedback_degradation",
        feedback_aggregate_revision=1,
        policy_hash="sha256:policy_default",
        status="PENDING",
    )
    await repo.create_improvement_request(req)

    outbox = SkillImprovementOutbox(
        outbox_id=f"outbox_{uuid.uuid4().hex[:12]}",
        request_id=req_id,
        workspace_id=workspace_id,
        state="PENDING",
    )
    repo._outbox[outbox.outbox_id] = outbox
    return req


async def only_scheduled_task(scheduler, task_type: str = "skill_improvement"):
    tasks = await scheduler.poll_due_tasks()
    for t in tasks:
        if isinstance(t.input_payload, dict) and t.input_payload.get("task_type") == task_type:
            return t
    raise RuntimeError(f"No task of type {task_type} found in scheduler")


async def _replace_source_skill_with_new_hash(plane, skill_id: str = "brief") -> str:
    modified_skill = SkillSpec(
        id=skill_id,
        version="1.0.0",
        instructions="Completely different instructions.",
        required_capabilities=[],
    )
    new_hash = f"sha256:{modified_skill.compute_hash()}"
    plane.spec_registry._by_version[("skill", skill_id, "1.0.0")] = PublishedSpecRecord(
        spec_kind="skill",
        spec_id=skill_id,
        version="1.0.0",
        definition_hash=new_hash,
        content=modified_skill.model_dump(mode="json"),
    )
    return new_hash


@pytest.mark.asyncio
async def test_relay_schedules_one_runless_task_with_request_coalescing_key() -> None:
    plane, _ = await _make_plane()
    request = await _queued_request(plane)
    scheduled = await relay_skill_improvement_outbox(plane, worker_id="relay-a", limit=10)
    assert request.request_id in scheduled

    task = await only_scheduled_task(plane.scheduler, task_type="skill_improvement")
    assert task.input_payload == {
        "task_type": "skill_improvement",
        "request_id": request.request_id,
        "workspace_id": "ws-a",
    }
    assert task.coalescing_key == f"skill-improvement:{request.request_id}"

    # Outbox marked delivered
    outbox_entries = list(plane.skill_improvement_repository._outbox.values())
    assert all(o.state == "DELIVERED" for o in outbox_entries)


@pytest.mark.asyncio
async def test_worker_refuses_stale_claim_or_changed_source_identity() -> None:
    plane, _ = await _make_plane()
    request = await _queued_request(plane)
    await relay_skill_improvement_outbox(plane, worker_id="relay-a", limit=10)
    task = await only_scheduled_task(plane.scheduler, task_type="skill_improvement")

    # Change source skill hash before execution
    await _replace_source_skill_with_new_hash(plane)

    result = await execute_skill_improvement_task(plane, task.input_payload)
    assert result.status == "STALE"
    assert result.safe_reason_code == "CHANGED_SOURCE_IDENTITY"
    assert await plane.skill_candidate_store.list_candidates("ws-a") == []


@pytest.mark.asyncio
async def test_concurrent_relays_do_not_duplicate_schedule() -> None:
    plane, _ = await _make_plane()
    request = await _queued_request(plane)

    # Worker A claims outbox
    claimed_a = await relay_skill_improvement_outbox(plane, worker_id="relay-a", limit=10)
    assert len(claimed_a) == 1

    # Worker B tries to claim same outbox (already delivered / claimed)
    claimed_b = await relay_skill_improvement_outbox(plane, worker_id="relay-b", limit=10)
    assert len(claimed_b) == 0

    # Scheduler has exactly one task
    tasks = await plane.scheduler.poll_due_tasks()
    assert len(tasks) == 1


@pytest.mark.asyncio
async def test_worker_refuses_stale_claim_when_already_finished() -> None:
    plane, _ = await _make_plane()
    request = await _queued_request(plane)
    await relay_skill_improvement_outbox(plane, worker_id="relay-a", limit=10)
    task = await only_scheduled_task(plane.scheduler, task_type="skill_improvement")

    # First execution succeeds
    result1 = await execute_skill_improvement_task(plane, task.input_payload)
    assert result1.status == "COMPLETED"

    # Second execution sees request already finished
    result2 = await execute_skill_improvement_task(plane, task.input_payload)
    assert result2.status == "STALE"
    assert result2.safe_reason_code == "REQUEST_ALREADY_FINISHED"


@pytest.mark.asyncio
async def test_unsupported_or_missing_payload() -> None:
    plane, _ = await _make_plane()
    result = await execute_skill_improvement_task(plane, {"task_type": "other"})
    assert result.status == "FAILED_REQUIRES_ATTENTION"
    assert result.safe_reason_code == "INVALID_PAYLOAD"

    result = await execute_skill_improvement_task(plane, {"task_type": "skill_improvement"})
    assert result.status == "FAILED_REQUIRES_ATTENTION"
    assert result.safe_reason_code == "INVALID_PAYLOAD"


@pytest.mark.asyncio
async def test_off_policy_returns_deferred_policy_disabled() -> None:
    plane, _ = await _make_plane(mode="OFF")
    request = await _queued_request(plane)
    await relay_skill_improvement_outbox(plane, worker_id="relay-a", limit=10)
    task = await only_scheduled_task(plane.scheduler, task_type="skill_improvement")

    result = await execute_skill_improvement_task(plane, task.input_payload)
    assert result.status == "DEFERRED_POLICY_DISABLED"
    assert result.safe_reason_code == "POLICY_OFF"
    assert await plane.skill_candidate_store.list_candidates("ws-a") == []


@pytest.mark.asyncio
async def test_no_usable_evaluator_returns_not_eligible() -> None:
    plane, _ = await _make_plane(with_evaluator=False)
    request = await _queued_request(plane)
    await relay_skill_improvement_outbox(plane, worker_id="relay-a", limit=10)
    task = await only_scheduled_task(plane.scheduler, task_type="skill_improvement")

    result = await execute_skill_improvement_task(plane, task.input_payload)
    assert result.status == "NOT_ELIGIBLE"
    assert result.safe_reason_code == "EVALUATOR_IDENTITY_MISMATCH"
    assert await plane.skill_candidate_store.list_candidates("ws-a") == []


@pytest.mark.asyncio
async def test_dispatch_one_task_runs_without_run_id_and_without_lease() -> None:
    plane, _ = await _make_plane()
    request = await _queued_request(plane)
    await relay_skill_improvement_outbox(plane, worker_id="relay-a", limit=10)
    task = await only_scheduled_task(plane.scheduler, task_type="skill_improvement")

    # dispatch_one_task handles skill_improvement without run_id and without lease
    await dispatch_one_task(plane, task)

    candidates = await plane.skill_candidate_store.list_candidates("ws-a")
    assert len(candidates) == 1
    assert candidates[0].status == SkillStatus.EVALUATED
    # Verified lease client was never called for a run lease
    lease_res = await plane.lease_client.acquire_lease("any_run", "worker_check")
    assert lease_res.success is True
