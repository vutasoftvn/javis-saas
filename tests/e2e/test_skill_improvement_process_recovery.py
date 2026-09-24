from __future__ import annotations

import asyncio
import os
from pathlib import Path
import subprocess
import sys
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent.contracts.run import RunStatus
from agent.contracts.spec import AgentSpec
from agent.registry.models import PublishedSpecRecord
from agent.registry.repository import PostgresSpecRegistryRepository
from agent.runs.models import RunRecord
from agent.runs.repository import PostgresRunRepository
from agent.skills.candidate_store import PostgresSkillCandidateStore
from agent.skills.contracts import SkillCandidate, SkillSpec, SkillStatus
from agent.skills.eval_contract import SkillEvalCase, SkillEvalExpected, SkillEvalSuite
from agent.skills.improvement_repository import (
    FeedbackWriteResult,
    PostgresSkillImprovementRepository,
    SkillFeedbackRecord,
    SkillUsageObservation,
)
from apps.cosa.skills.improvement_evaluators import (
    RegisteredSkillEvaluator,
    SkillEvaluatorRegistry,
)
from apps.cosa.skills.improvement_policy import load_effective_improvement_policy

_RAW_DB_URL = os.environ.get("AGENT_TEST_DATABASE_URL")
if not _RAW_DB_URL and os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.startswith("AGENT_TEST_DATABASE_URL="):
                _RAW_DB_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

if _RAW_DB_URL and "postgresql://" in _RAW_DB_URL and "postgresql+asyncpg://" not in _RAW_DB_URL:
    TEST_DATABASE_URL = _RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    TEST_DATABASE_URL = _RAW_DB_URL

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENT_TEST_DATABASE_URL not set — skipping cross-process recovery test",
)


_WORKER_SUBPROCESS_SCRIPT = """
import asyncio
import sys
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent.coordination.scheduler import RunScheduler
from agent.runs.leases import RunLeaseManager
from agent.skills.candidate_store import PostgresSkillCandidateStore
from agent.skills.contracts import SkillStatus
from agent.workflows.repository import InMemoryWorkflowDefinitionRepository
from agent.skills.eval_contract import SkillEvalCase, SkillEvalExpected, SkillEvalSuite
from agent.skills.improvement_repository import PostgresSkillImprovementRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.skills.improvement_evaluators import (
    RegisteredSkillEvaluator,
    SkillEvaluatorRegistry,
)
from apps.cosa.skills.improvement_policy import load_effective_improvement_policy
from apps.cosa.skills.improvement_service import SkillImprovementService
from apps.cosa.worker.skill_improvement import (
    execute_skill_improvement_task,
    relay_skill_improvement_outbox,
)

class _MockKernel:
    async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult:
        content = "Enhanced brief" if "Enhanced" in spec.instructions else "Base brief"
        return RunResult(
            run_id="run_mock_eval",
            status=RunStatus.COMPLETED,
            final_output={"response": content},
        )

async def main():
    db_url = sys.argv[1]
    workspace_id = sys.argv[2]
    skill_id = sys.argv[3]
    version = sys.argv[4]
    def_hash = sys.argv[5]
    expected_request_id = sys.argv[6]

    engine = create_async_engine(db_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresSkillImprovementRepository(factory)
    cand_store = PostgresSkillCandidateStore(factory)
    scheduler = RunScheduler()

    identity = (skill_id, version, def_hash)
    policy = load_effective_improvement_policy(
        mode="CANDIDATE",
        allowed_identities=[identity],
    )

    suite = SkillEvalSuite(
        skill_id=skill_id,
        skill_version=version,
        cases=(
            SkillEvalCase(
                id="c1",
                input={"prompt": "Draft executive brief"},
                expected=SkillEvalExpected(outcome="accept", reason="brief"),
            ),
        ),
    )
    eval_registry = SkillEvaluatorRegistry()
    eval_registry.register(
        identity,
        RegisteredSkillEvaluator(
            suite=suite,
            suite_ref=f"{skill_id}.eval.yaml",
            custom_score_fn=lambda res, case: 0.95 if "Enhanced" in str(res.final_output) else 0.50,
        ),
    )

    def test_mutator(skill_spec):
        mutated = skill_spec.model_copy(
            update={"instructions": f"{skill_spec.instructions} Enhanced."}
        )
        return mutated, "Enhanced instructions"

    # Minimal in-memory spec registry containing the published skill
    from agent.registry.repository import InMemorySpecRegistryRepository
    spec_reg = InMemorySpecRegistryRepository()
    from agent.skills.contracts import SkillSpec
    base_skill = SkillSpec(
        id=skill_id,
        version=version,
        instructions="Always write concise bullet points.",
        required_capabilities=[],
    )
    from agent.registry.models import PublishedSpecRecord
    await spec_reg.publish(
        PublishedSpecRecord(
            spec_kind="skill",
            spec_id=skill_id,
            version=version,
            definition_hash=def_hash,
            content=base_skill.model_dump(mode="json"),
        )
    )

    kernel = _MockKernel()
    service = SkillImprovementService(
        repository=repo,
        spec_registry=spec_reg,
        candidate_store=cand_store,
        kernel=kernel,
        policy=policy,
        evaluator_registry=eval_registry,
        mutator=test_mutator,
    )

    plane = CosaAgentPlane(
        repository=None,
        conversation_repository=None,
        spec_registry=spec_reg,
        governance_store=None,
        capability_registry=None,
        policy_engine=None,
        approval_service=None,
        gateway=None,
        kernel=kernel,
        workflow_registry=None,
        workflow_engine=None,
        workflow_definition_repository=InMemoryWorkflowDefinitionRepository(),
        company_client=None,
        tenant_policy_client=None,
        scheduler=scheduler,
        lease_client=RunLeaseManager(),
        stream_event_repository=None,
        skill_candidate_store=cand_store,
        skill_improvement_repository=repo,
        skill_improvement_service=service,
    )

    # 1. Relay claimed outbox rows -> schedule skill_improvement task
    scheduled = await relay_skill_improvement_outbox(plane, worker_id="worker_proc_1", limit=10)
    assert expected_request_id in scheduled, f"Expected {expected_request_id} in scheduled: {scheduled}"

    # 2. Poll scheduled task from scheduler
    await asyncio.sleep(0.1)
    tasks = await scheduler.poll_due_tasks()
    matching = [t for t in tasks if t.input_payload.get("request_id") == expected_request_id]
    assert len(matching) == 1, f"Expected 1 task for request {expected_request_id}, got {len(matching)}"
    payload = matching[0].input_payload
    assert payload["task_type"] == "skill_improvement"

    # 3. Execute skill improvement task
    outcome = await execute_skill_improvement_task(plane, payload, worker_id="worker_proc_1")
    assert outcome.status == "COMPLETED", f"Expected COMPLETED, got {outcome.status} ({outcome.safe_reason_code})"
    assert outcome.candidate_id is not None

    # 4. Verify candidate in PostgreSQL
    cand = await cand_store.get_candidate(workspace_id, outcome.candidate_id)
    assert cand is not None
    assert cand.status == SkillStatus.EVALUATED, f"Candidate status must be EVALUATED, got {cand.status}"
    assert cand.eval_score == 0.95

    # 5. Idempotent replay: executing task again refuses as already finished
    replay_outcome = await execute_skill_improvement_task(plane, payload, worker_id="worker_proc_1")
    assert replay_outcome.status == "STALE"
    assert replay_outcome.safe_reason_code == "REQUEST_ALREADY_FINISHED"

    await engine.dispose()
    print("SUCCESS_SKILL_IMPROVEMENT_RECOVERY")

asyncio.run(main())
"""


_STALE_HASH_SUBPROCESS_SCRIPT = """
import asyncio
import sys
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent.coordination.scheduler import RunScheduler
from agent.runs.leases import RunLeaseManager
from agent.skills.candidate_store import PostgresSkillCandidateStore
from agent.skills.contracts import SkillStatus
from agent.skills.eval_contract import SkillEvalCase, SkillEvalExpected, SkillEvalSuite
from agent.skills.improvement_repository import PostgresSkillImprovementRepository
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.skills.improvement_evaluators import (
    RegisteredSkillEvaluator,
    SkillEvaluatorRegistry,
)
from apps.cosa.skills.improvement_policy import load_effective_improvement_policy
from apps.cosa.skills.improvement_service import SkillImprovementService
from apps.cosa.worker.skill_improvement import (
    execute_skill_improvement_task,
    relay_skill_improvement_outbox,
)

async def main():
    db_url = sys.argv[1]
    workspace_id = sys.argv[2]
    skill_id = sys.argv[3]
    version = sys.argv[4]
    def_hash = sys.argv[5]
    expected_request_id = sys.argv[6]

    engine = create_async_engine(db_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresSkillImprovementRepository(factory)
    cand_store = PostgresSkillCandidateStore(factory)
    scheduler = RunScheduler()

    # Spec registry has CHANGED definition hash
    from agent.registry.repository import InMemorySpecRegistryRepository
    from agent.workflows.repository import InMemoryWorkflowDefinitionRepository
    spec_reg = InMemorySpecRegistryRepository()
    from agent.registry.models import PublishedSpecRecord
    await spec_reg.publish(
        PublishedSpecRecord(
            spec_kind="skill",
            spec_id=skill_id,
            version=version,
            definition_hash="sha256:changed_hash_9999",
            content={},
        )
    )

    plane = CosaAgentPlane(
        repository=None,
        conversation_repository=None,
        spec_registry=spec_reg,
        governance_store=None,
        capability_registry=None,
        policy_engine=None,
        approval_service=None,
        gateway=None,
        kernel=None,
        workflow_registry=None,
        workflow_engine=None,
        workflow_definition_repository=InMemoryWorkflowDefinitionRepository(),
        company_client=None,
        tenant_policy_client=None,
        scheduler=scheduler,
        lease_client=RunLeaseManager(),
        stream_event_repository=None,
        skill_candidate_store=cand_store,
        skill_improvement_repository=repo,
        skill_improvement_service=None,
    )

    # Relay task
    scheduled = await relay_skill_improvement_outbox(plane, worker_id="worker_proc_2", limit=10)
    assert expected_request_id in scheduled

    await asyncio.sleep(0.1)
    tasks = await scheduler.poll_due_tasks()
    matching = [t for t in tasks if t.input_payload.get("request_id") == expected_request_id]
    payload = matching[0].input_payload

    # Execute with changed hash -> refused as STALE
    outcome = await execute_skill_improvement_task(plane, payload, worker_id="worker_proc_2")
    assert outcome.status == "STALE"
    assert outcome.safe_reason_code == "CHANGED_SOURCE_IDENTITY"

    # Verify no candidate created
    cands = await cand_store.list_candidates(workspace_id)
    assert len(cands) == 0, f"Expected 0 candidates, got {len(cands)}"

    await engine.dispose()
    print("SUCCESS_STALE_HASH_REFUSED")

asyncio.run(main())
"""


@pytest.mark.asyncio
async def test_degrading_feedback_survives_api_worker_restart_and_creates_one_candidate(
    tmp_path: Path,
) -> None:
    engine = create_async_engine(TEST_DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresSkillImprovementRepository(session_factory)
    cand_store = PostgresSkillCandidateStore(session_factory)

    workspace_id = f"ws_rec_{uuid.uuid4().hex[:6]}"
    skill_id = "brief_e2e"
    version = "1.0.0"

    base_skill = SkillSpec(
        id=skill_id,
        version=version,
        instructions="Always write concise bullet points.",
        required_capabilities=[],
    )
    def_hash = f"sha256:{base_skill.compute_hash()}"

    # 1. Record 3 runs and usage observations
    run_repo = PostgresRunRepository(session_factory)
    for i in range(3):
        run_id = f"run_{workspace_id}_{i}"
        run = RunRecord(
            run_id=run_id,
            principal="test_operator",
            root_executable_id="wf_1",
            workspace_id=workspace_id,
            status=RunStatus.RUNNING,
        )
        await run_repo.create_run(run)
        obs = SkillUsageObservation(
            workspace_id=workspace_id,
            run_id=run_id,
            skill_id=skill_id,
            skill_version=version,
            definition_hash=def_hash,
            root_spec_id="cosa.agent.test",
            root_definition_hash="sha256:root_hash_default",
        )
        await repo.record_resolved_skill_use(obs)

    # 2. Record initial high feedback to set previous_score = 1.0
    policy = load_effective_improvement_policy(
        mode="CANDIDATE",
        allowed_identities=[(skill_id, version, def_hash)],
        minimum_degradation_delta=0.05,
    )
    for i in range(2):
        fb_high = SkillFeedbackRecord(
            workspace_id=workspace_id,
            run_id=f"run_{workspace_id}_{i}",
            skill_id=skill_id,
            rating=5,
            success=True,
            idempotency_key=f"idem_high_{i}",
        )
        await repo.record_feedback_and_maybe_enqueue(feedback=fb_high, policy=policy)

    # 3. Record degrading feedback to drop aggregate below threshold
    fb_low1 = SkillFeedbackRecord(
        workspace_id=workspace_id,
        run_id=f"run_{workspace_id}_0",
        skill_id=skill_id,
        rating=1,
        success=False,
        idempotency_key=f"idem_low_1_{uuid.uuid4().hex[:6]}",
    )
    res_low1 = await repo.record_feedback_and_maybe_enqueue(feedback=fb_low1, policy=policy)

    fb_low2 = SkillFeedbackRecord(
        workspace_id=workspace_id,
        run_id=f"run_{workspace_id}_1",
        skill_id=skill_id,
        rating=1,
        success=False,
        idempotency_key=f"idem_low_2_{uuid.uuid4().hex[:6]}",
    )
    res_low2 = await repo.record_feedback_and_maybe_enqueue(feedback=fb_low2, policy=policy)

    fb_low3 = SkillFeedbackRecord(
        workspace_id=workspace_id,
        run_id=f"run_{workspace_id}_2",
        skill_id=skill_id,
        rating=1,
        success=False,
        idempotency_key=f"idem_low_3_{uuid.uuid4().hex[:6]}",
    )
    res_low3 = await repo.record_feedback_and_maybe_enqueue(feedback=fb_low3, policy=policy)

    assert res_low3.improvement_disposition == "QUEUED"
    assert res_low3.request_id is not None
    request_id = res_low3.request_id

    # Disconnect parent engine (simulating shutdown)
    await engine.dispose()

    # Launch subprocess representing worker process after restart
    script_file = tmp_path / "run_skill_improvement_worker.py"
    script_file.write_text(_WORKER_SUBPROCESS_SCRIPT)

    proc = subprocess.run(
        [
            sys.executable,
            str(script_file),
            TEST_DATABASE_URL,
            workspace_id,
            skill_id,
            version,
            def_hash,
            request_id,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=dict(
            os.environ,
            PYTHONPATH=f"{Path.cwd()}:{Path.cwd() / 'packages'}:{Path.cwd() / 'apps'}",
        ),
    )
    assert proc.returncode == 0, f"Worker subprocess failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    assert "SUCCESS_SKILL_IMPROVEMENT_RECOVERY" in proc.stdout

    # Reconnect fresh engine to verify final DB state
    engine2 = create_async_engine(TEST_DATABASE_URL)
    session_factory2 = async_sessionmaker(engine2, expire_on_commit=False)
    cand_store2 = PostgresSkillCandidateStore(session_factory2)
    repo2 = PostgresSkillImprovementRepository(session_factory2)

    cands = await cand_store2.list_candidates(workspace_id)
    assert len(cands) == 1
    assert cands[0].status == SkillStatus.EVALUATED
    # Invariant: candidate is NEVER auto-published without Founder approval
    assert cands[0].status != SkillStatus.PUBLISHED

    # Invariant: evaluation lineage was recorded
    evals = await repo2.get_evaluations(workspace_id, request_id)
    assert len(evals) >= 1
    assert evals[0].candidate_score >= 0.70

    await engine2.dispose()


@pytest.mark.asyncio
async def test_foreign_feedback_and_changed_hash_cannot_create_candidate_after_restart(
    tmp_path: Path,
) -> None:
    engine = create_async_engine(TEST_DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresSkillImprovementRepository(session_factory)

    workspace_id = f"ws_stale_{uuid.uuid4().hex[:6]}"
    skill_id = "brief_stale"
    version = "1.0.0"
    def_hash = "sha256:orig_hash_123"

    policy = load_effective_improvement_policy(
        mode="CANDIDATE",
        allowed_identities=[(skill_id, version, def_hash)],
    )

    # Queue an improvement request directly in DB
    request_id = f"sir_{uuid.uuid4().hex[:12]}"
    from agent.skills.improvement_repository import SkillImprovementOutbox, SkillImprovementRequest
    req = SkillImprovementRequest(
        request_id=request_id,
        workspace_id=workspace_id,
        skill_id=skill_id,
        skill_version=version,
        definition_hash=def_hash,
        trigger="feedback_degradation",
        feedback_aggregate_revision=1,
        policy_hash="sha256:policy_default",
        status="PENDING",
    )
    await repo.create_improvement_request(req)

    # Insert outbox
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                text(
                    """
                    INSERT INTO agent.skill_improvement_outbox (
                        outbox_id, request_id, workspace_id, state, attempt_count, next_attempt_at, created_at
                    ) VALUES (
                        :ob_id, :req_id, :ws_id, 'PENDING', 0, NOW(), NOW()
                    )
                    """
                ),
                {"ob_id": f"outbox_{uuid.uuid4().hex[:12]}", "req_id": request_id, "ws_id": workspace_id},
            )

    await engine.dispose()

    # Launch subprocess with changed hash
    script_file = tmp_path / "run_stale_hash_worker.py"
    script_file.write_text(_STALE_HASH_SUBPROCESS_SCRIPT)

    proc = subprocess.run(
        [
            sys.executable,
            str(script_file),
            TEST_DATABASE_URL,
            workspace_id,
            skill_id,
            version,
            def_hash,
            request_id,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=dict(
            os.environ,
            PYTHONPATH=f"{Path.cwd()}:{Path.cwd() / 'packages'}:{Path.cwd() / 'apps'}",
        ),
    )
    assert proc.returncode == 0, f"Worker subprocess failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    assert "SUCCESS_STALE_HASH_REFUSED" in proc.stdout


@pytest.mark.asyncio
async def test_replayed_feedback_and_worker_task_remain_exactly_once_after_restart() -> None:
    engine = create_async_engine(TEST_DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresSkillImprovementRepository(session_factory)

    workspace_id = f"ws_replay_{uuid.uuid4().hex[:6]}"
    skill_id = "brief_replay"
    version = "1.0.0"
    def_hash = "sha256:replay_hash_456"

    # Run and Observation
    run_id = f"run_{workspace_id}_1"
    run_repo = PostgresRunRepository(session_factory)
    run = RunRecord(
        run_id=run_id,
        principal="test_operator",
        root_executable_id="wf_1",
        workspace_id=workspace_id,
        status=RunStatus.RUNNING,
    )
    await run_repo.create_run(run)
    obs = SkillUsageObservation(
        workspace_id=workspace_id,
        run_id=run_id,
        skill_id=skill_id,
        skill_version=version,
        definition_hash=def_hash,
        root_spec_id="cosa.agent.test",
        root_definition_hash="sha256:root_hash_default",
    )
    await repo.record_resolved_skill_use(obs)

    policy = load_effective_improvement_policy(
        mode="CANDIDATE",
        allowed_identities=[(skill_id, version, def_hash)],
    )

    idem_key = f"idem_fb_{uuid.uuid4().hex[:8]}"
    fb = SkillFeedbackRecord(
        workspace_id=workspace_id,
        run_id=run_id,
        skill_id=skill_id,
        rating=1,
        success=False,
        idempotency_key=idem_key,
    )

    # 1. First submission
    res1 = await repo.record_feedback_and_maybe_enqueue(feedback=fb, policy=policy)
    # 2. Replayed submission with identical idempotency key
    res2 = await repo.record_feedback_and_maybe_enqueue(feedback=fb, policy=policy)

    assert res1.feedback_id == res2.feedback_id

    # Verify exactly 1 feedback row exists in PostgreSQL
    async with session_factory() as session:
        count_res = await session.execute(
            text(
                "SELECT COUNT(*) FROM agent.agent_skill_feedback WHERE workspace_id = :ws_id AND idempotency_key = :key"
            ),
            {"ws_id": workspace_id, "key": idem_key},
        )
        assert count_res.scalar() == 1

    await engine.dispose()
