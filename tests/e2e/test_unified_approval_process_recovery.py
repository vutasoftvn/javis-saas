from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent.contracts.run import RunStatus
from agent.runs.models import (
    ApprovalSubject,
    RunApprovalRecord,
    RunCheckpointRecord,
    RunRecord,
    RunToolCallRecord,
)
from agent.runs.repository import PostgresRunRepository
from agent.skills.candidate_store import PostgresSkillCandidateStore
from agent.skills.contracts import SkillCandidate, SkillSpec, SkillStatus

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


_TOOL_CALL_SUBPROCESS_SCRIPT = """
import asyncio
import sys
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from agent.capabilities.approval_service import ApprovalService
from agent.runs.repository import PostgresRunRepository

async def main():
    db_url = sys.argv[1]
    run_id = sys.argv[2]
    call_1_id = sys.argv[3]
    call_2_id = sys.argv[4]
    checkpoint_ref = sys.argv[5]

    engine = create_async_engine(db_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresRunRepository(factory)
    approval_svc = ApprovalService(repo)

    # 1. verify_and_prepare_resume on call_1 (approved) -> can_resume=True
    res1 = await approval_svc.verify_and_prepare_resume(
        run_id=run_id,
        tool_call_id=call_1_id,
        checkpoint_ref=checkpoint_ref,
    )
    assert res1.can_resume is True, f"call_1 should be resumable, got {res1.reason_code}"
    assert res1.approval_record is not None
    assert res1.approval_record.status == "approved"

    # 2. verify_and_prepare_resume on call_2 (not approved) -> can_resume=False
    res2 = await approval_svc.verify_and_prepare_resume(
        run_id=run_id,
        tool_call_id=call_2_id,
        checkpoint_ref=checkpoint_ref,
    )
    assert res2.can_resume is False, f"call_2 should NOT be resumable, got {res2.reason_code}"

    await engine.dispose()
    print("SUCCESS_TOOL_CALL_RESUME")

asyncio.run(main())
"""


@pytest.mark.asyncio
async def test_tool_call_resume_only_runs_matching_invocation(tmp_path: Path) -> None:
    engine = create_async_engine(TEST_DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresRunRepository(session_factory)

    run_id = f"run_rec_{uuid.uuid4().hex[:8]}"
    workspace_id = f"ws_tc_{uuid.uuid4().hex[:6]}"
    call_1_id = f"call_1_{uuid.uuid4().hex[:6]}"
    call_2_id = f"call_2_{uuid.uuid4().hex[:6]}"
    checkpoint_ref = f"ckpt_{uuid.uuid4().hex[:8]}"

    # Setup parent state in DB
    run = RunRecord(
        run_id=run_id,
        principal="test_operator",
        root_executable_id="wf_1",
        workspace_id=workspace_id,
        status=RunStatus.WAITING_APPROVAL,
    )
    await repo.create_run(run)

    ckpt = RunCheckpointRecord(
        checkpoint_ref=checkpoint_ref,
        run_id=run_id,
        sequence_no=1,
    )
    await repo.save_checkpoint(ckpt)

    tc1 = RunToolCallRecord(
        tool_call_id=call_1_id,
        run_id=run_id,
        checkpoint_ref=checkpoint_ref,
        capability_id="workspace.exec",
        payload_hash="hash_1",
        input_payload={"cmd": "ls"},
        status="pending",
    )
    await repo.save_tool_call(tc1)

    tc2 = RunToolCallRecord(
        tool_call_id=call_2_id,
        run_id=run_id,
        checkpoint_ref=checkpoint_ref,
        capability_id="workspace.exec",
        payload_hash="hash_2",
        input_payload={"cmd": "rm"},
        status="pending",
    )
    await repo.save_tool_call(tc2)

    # Create approval strictly bound to call_1
    approval = RunApprovalRecord(
        approval_id=f"appr_{uuid.uuid4().hex[:8]}",
        workspace_id=workspace_id,
        binding_kind="TOOL_CALL",
        run_id=run_id,
        tool_call_id=call_1_id,
        checkpoint_ref=checkpoint_ref,
        action="tool_execution",
        subject_kind="tool_call",
        subject_ref=call_1_id,
        status="pending",
    )
    await repo.create_approval(approval)
    await repo.decide_approval(
        approval.approval_id,
        reviewer="founder_user",
        approved=True,
    )

    # Disconnect parent engine (simulating shutdown)
    await engine.dispose()

    # Launch subprocess with clean environment and fresh DB connection
    script_file = tmp_path / "run_tool_call_resume.py"
    script_file.write_text(_TOOL_CALL_SUBPROCESS_SCRIPT)

    proc = subprocess.run(
        [
            sys.executable,
            str(script_file),
            TEST_DATABASE_URL,
            run_id,
            call_1_id,
            call_2_id,
            checkpoint_ref,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=dict(
            os.environ,
            PYTHONPATH=f"{Path.cwd()}:{Path.cwd() / 'packages'}:{Path.cwd() / 'apps'}",
        ),
    )
    assert proc.returncode == 0, f"Subprocess failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    assert "SUCCESS_TOOL_CALL_RESUME" in proc.stdout


_PROMOTION_RECOVERY_SUBPROCESS_SCRIPT = """
import asyncio
import sys
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from agent.capabilities.approval_service import ApprovalService
from agent.coordination.scheduler import RunScheduler
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import PostgresRunRepository
from agent.runs.stream_events import PostgresRunStreamEventRepository
from agent.skills.candidate_store import PostgresSkillCandidateStore
from agent.skills.contracts import SkillStatus
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.worker.approval_actions import (
    execute_skill_candidate_promotion,
    relay_approved_actions,
)

async def main():
    db_url = sys.argv[1]
    workspace_id = sys.argv[2]
    candidate_id = sys.argv[3]
    expected_approval_id = sys.argv[4]

    engine = create_async_engine(db_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresRunRepository(factory)
    cand_store = PostgresSkillCandidateStore(factory)
    stream_repo = PostgresRunStreamEventRepository(factory)
    approval_svc = ApprovalService(repo)
    scheduler = RunScheduler()

    plane = CosaAgentPlane(
        repository=repo,
        conversation_repository=None,
        spec_registry=None,
        governance_store=None,
        capability_registry=None,
        policy_engine=None,
        approval_service=approval_svc,
        gateway=None,
        kernel=None,
        workflow_registry=None,
        workflow_engine=None,
        company_client=None,
        tenant_policy_client=None,
        scheduler=scheduler,
        lease_client=RunLeaseManager(),
        stream_event_repository=stream_repo,
    )
    plane.skill_candidate_store = cand_store

    # 1. Relay claimed outbox rows -> schedule approval_action task
    scheduled = await relay_approved_actions(plane, worker_id="worker_proc_1", limit=10)
    assert expected_approval_id in scheduled, f"Expected {expected_approval_id} in scheduled: {scheduled}"

    # Poll task from scheduler (slight sleep to guarantee now >= run_at)
    await asyncio.sleep(0.1)
    tasks = await scheduler.poll_due_tasks()
    matching_tasks = [t for t in tasks if t.input_payload.get("approval_id") == expected_approval_id]
    assert len(matching_tasks) == 1, f"Expected 1 task for {expected_approval_id}, got {len(matching_tasks)}"
    task_payload = matching_tasks[0].input_payload
    assert task_payload["task_type"] == "approval_action"

    # 2. Execute promotion
    res1 = await execute_skill_candidate_promotion(plane, task_payload)
    assert res1.success is True, f"Promotion failed: {res1.reason_code}"
    assert res1.reason_code == "PUBLISHED"

    # 3. Idempotent replay (simulate worker restart/crash)
    res2 = await execute_skill_candidate_promotion(plane, task_payload)
    assert res2.success is True, f"Replay failed: {res2.reason_code}"
    assert res2.reason_code == "ALREADY_PUBLISHED"

    # 4. Verify candidate in PostgreSQL
    cand = await cand_store.get_candidate(workspace_id, candidate_id)
    assert cand is not None
    assert cand.status == SkillStatus.PUBLISHED
    assert cand.promotion_approval_id == expected_approval_id

    await engine.dispose()
    print("SUCCESS_PROMOTION_RECOVERY")

asyncio.run(main())
"""


@pytest.mark.asyncio
async def test_promotion_recovers_between_decision_and_action(tmp_path: Path) -> None:
    engine = create_async_engine(TEST_DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresRunRepository(session_factory)
    cand_store = PostgresSkillCandidateStore(session_factory)

    workspace_id = f"ws_pr_{uuid.uuid4().hex[:6]}"
    candidate_id = f"cand_rec_{uuid.uuid4().hex[:6]}"

    spec = SkillSpec(
        id=f"skill_{candidate_id}",
        version="1.0.0",
        name="Recoverable Skill",
        description="Recovers across restart",
        instructions="Analyze logs durably.",
        required_capabilities=[],
    )
    cand = SkillCandidate(
        candidate_id=candidate_id,
        parent_run_id=f"run_{uuid.uuid4().hex[:6]}",
        proposed_skill=spec,
        eval_score=0.95,
        status=SkillStatus.EVALUATED,
    )
    saved = await cand_store.save_candidate(workspace_id, cand)

    approval_id = f"appr_pr_{uuid.uuid4().hex[:8]}"
    approval = RunApprovalRecord(
        approval_id=approval_id,
        workspace_id=workspace_id,
        binding_kind="CHANGE_REQUEST",
        run_id=None,
        action="promote_skill_candidate",
        subject_kind="skill_candidate",
        subject_ref=candidate_id,
        subject_hash=saved.definition_hash,
        requirement={"role": "founder"},
        status="pending",
    )
    await repo.create_approval(approval)

    # Decide approval and insert into outbox
    decided = await repo.decide_change_approval_and_enqueue(
        approval_id=approval_id,
        reviewer="founder_lead",
        approved=True,
    )
    assert decided is not None

    # Disconnect parent process
    await engine.dispose()

    # Launch subprocess to perform relay and promotion execution
    script_file = tmp_path / "run_promotion_recovery.py"
    script_file.write_text(_PROMOTION_RECOVERY_SUBPROCESS_SCRIPT)

    proc = subprocess.run(
        [
            sys.executable,
            str(script_file),
            TEST_DATABASE_URL,
            workspace_id,
            candidate_id,
            approval_id,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=dict(
            os.environ,
            PYTHONPATH=f"{Path.cwd()}:{Path.cwd() / 'packages'}:{Path.cwd() / 'apps'}",
        ),
    )
    assert proc.returncode == 0, f"Subprocess failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    assert "SUCCESS_PROMOTION_RECOVERY" in proc.stdout


_STALE_REJECTION_SUBPROCESS_SCRIPT = """
import asyncio
import sys
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from agent.capabilities.approval_service import ApprovalService
from agent.coordination.scheduler import RunScheduler
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import PostgresRunRepository
from agent.runs.stream_events import PostgresRunStreamEventRepository
from agent.skills.candidate_store import PostgresSkillCandidateStore
from agent.skills.contracts import SkillStatus
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.worker.approval_actions import execute_skill_candidate_promotion

async def main():
    db_url = sys.argv[1]
    workspace_id = sys.argv[2]
    candidate_id = sys.argv[3]
    approval_id = sys.argv[4]
    original_hash = sys.argv[5]

    engine = create_async_engine(db_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresRunRepository(factory)
    cand_store = PostgresSkillCandidateStore(factory)
    stream_repo = PostgresRunStreamEventRepository(factory)
    approval_svc = ApprovalService(repo)

    plane = CosaAgentPlane(
        repository=repo,
        conversation_repository=None,
        spec_registry=None,
        governance_store=None,
        capability_registry=None,
        policy_engine=None,
        approval_service=approval_svc,
        gateway=None,
        kernel=None,
        workflow_registry=None,
        workflow_engine=None,
        company_client=None,
        tenant_policy_client=None,
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=stream_repo,
    )
    plane.skill_candidate_store = cand_store

    # 1. Foreign workspace attempt fails
    foreign_payload = {
        "task_type": "approval_action",
        "approval_id": approval_id,
        "workspace_id": "ws_attacker_forged",
        "action": "promote_skill_candidate",
        "subject_kind": "skill_candidate",
        "subject_ref": candidate_id,
        "subject_hash": original_hash,
    }
    foreign_res = await execute_skill_candidate_promotion(plane, foreign_payload)
    assert foreign_res.success is False
    assert foreign_res.reason_code == "CANDIDATE_NOT_FOUND"

    # 2. Mutate candidate instruction directly to simulate tampering after approval
    cand = await cand_store.get_candidate(workspace_id, candidate_id)
    cand.proposed_skill.instructions = "MALICIOUS MODIFIED INSTRUCTION"
    cand.definition_hash = f"sha256:{cand.proposed_skill.compute_hash()}"
    await cand_store.save_candidate(workspace_id, cand)

    # 3. Attempt execution with genuine workspace but now-stale approval subject hash
    stale_payload = {
        "task_type": "approval_action",
        "approval_id": approval_id,
        "workspace_id": workspace_id,
        "action": "promote_skill_candidate",
        "subject_kind": "skill_candidate",
        "subject_ref": candidate_id,
        "subject_hash": original_hash,
    }
    stale_res = await execute_skill_candidate_promotion(plane, stale_payload)
    assert stale_res.success is False
    assert stale_res.reason_code == "APPROVAL_SUBJECT_STALE"

    # 4. Verify candidate was NOT published
    final_cand = await cand_store.get_candidate(workspace_id, candidate_id)
    assert final_cand.status != SkillStatus.PUBLISHED
    assert final_cand.promotion_approval_id is None

    await engine.dispose()
    print("SUCCESS_REJECTION_RECOVERY")

asyncio.run(main())
"""


_GOVERNED_WORKFLOW_RESUME_SUBPROCESS_SCRIPT = """
import asyncio
import sys
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent.capabilities.approval_service import DurableApprovalService
from agent.runs.repository import PostgresRunRepository
from agent.workflows.engine import WorkflowEngine
from agent.workflows.postgres_repository import PostgresWorkflowDefinitionRepository

from apps.cosa.composition.workflow_orchestration import WorkflowOrchestration
from apps.cosa.worker.governed_workflow_run import execute_governed_workflow_run

AGENT_SPEC_ID = "agentspec-recovery-1"


class RevokedDeploymentResolver:
    # Task 11 — a fresh process reloading the SAME manifest/checkpoint by
    # run_id, but now sees the deployment PAUSED: the resumed AGENT effect
    # must fail closed instead of trusting the ACTIVE state seen before pause.
    async def resolve_authority(self, workspace_id, project_id, deployment_id):
        return {
            "state": "PAUSED",
            "workspaceId": workspace_id,
            "projectId": project_id,
            "agentSpec": {"id": AGENT_SPEC_ID, "version": "1.0.0", "definitionHash": "hash1"},
        }


class UnusedKernel:
    async def run(self, request):
        raise AssertionError("kernel must never be invoked once the deployment is revoked")


async def main():
    db_url = sys.argv[1]
    run_id = sys.argv[2]

    engine = create_async_engine(db_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    run_repository = PostgresRunRepository(factory)
    workflow_definition_repository = PostgresWorkflowDefinitionRepository(factory)
    approval_service = DurableApprovalService(run_repository)
    workflow_engine = WorkflowEngine(
        resolver=RevokedDeploymentResolver(),
        kernel=UnusedKernel(),
        approval_service=approval_service,
    )
    workflow_orchestration = WorkflowOrchestration(
        gateway=None,
        workflow_engine=workflow_engine,
        workflow_registry=None,
        approval_service=approval_service,
        workflow_definition_repository=workflow_definition_repository,
    )
    plane = SimpleNamespace(
        run_repository=run_repository,
        workflow_orchestration=workflow_orchestration,
    )

    # Reload the manifest fresh from Postgres by run_id ONLY — this process
    # never saw the in-memory manifest object the parent process built.
    manifest = await run_repository.get_workflow_manifest(run_id)
    assert manifest is not None, f"no durable manifest found for run_id={run_id}"

    outcome = await execute_governed_workflow_run(plane, manifest)
    assert outcome.status == "failed", f"expected resume to fail closed, got {outcome.status}"

    run = await run_repository.get_run(run_id)
    assert run.status.value == "failed"

    await engine.dispose()
    print("SUCCESS_GOVERNED_WORKFLOW_RESUME")

asyncio.run(main())
"""


@pytest.mark.asyncio
async def test_governed_workflow_run_resumes_pinned_state_and_revoked_deployment_blocks_effect(
    tmp_path: Path,
) -> None:
    """Task 11 — a governed workflow run paused at an APPROVAL_GATE, approved,
    then resumed in a BRAND NEW PROCESS after the project agent deployment was
    revoked: the resumed AGENT effect must fail closed, and the run/checkpoint
    it resumes from must be the exact durable state the first process left
    behind (not a fresh reconstruction)."""
    import uuid as uuid_mod
    from types import SimpleNamespace

    from agent.capabilities.approval_service import DurableApprovalService
    from agent.runs.repository import PostgresRunRepository
    from agent.workflows.engine import WorkflowEngine
    from agent.workflows.manifest import make_manifest
    from agent.workflows.postgres_repository import PostgresWorkflowDefinitionRepository
    from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec

    from apps.cosa.composition.workflow_orchestration import WorkflowOrchestration
    from apps.cosa.worker.governed_workflow_run import execute_governed_workflow_run

    engine = create_async_engine(TEST_DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    run_repository = PostgresRunRepository(session_factory)
    workflow_definition_repository = PostgresWorkflowDefinitionRepository(session_factory)
    approval_service = DurableApprovalService(run_repository)

    workspace_id = f"ws_gwf_{uuid_mod.uuid4().hex[:6]}"
    project_id = f"proj_gwf_{uuid_mod.uuid4().hex[:6]}"
    deployment_id = f"dep_gwf_{uuid_mod.uuid4().hex[:6]}"
    workflow_id = f"wf_gwf_{uuid_mod.uuid4().hex[:6]}"
    run_id = f"run_gwf_{uuid_mod.uuid4().hex[:8]}"

    spec = WorkflowSpec(
        id=workflow_id,
        name="Governed Recovery Workflow",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="approve",
                type=StepType.APPROVAL_GATE,
                subject_key="workspace_id",
                action="run_governed_effect",
            ),
            WorkflowStepSpec(
                id="agent_step",
                type=StepType.AGENT,
                depends_on=["approve"],
                project_agent_deployment_id=deployment_id,
                output_key="agent_output",
            ),
        ],
    ).with_hash()
    await workflow_definition_repository.save_definition(spec, workspace_id=workspace_id)

    manifest = await run_repository.create_workflow_manifest(
        make_manifest(
            run_id=run_id,
            project_id=project_id,
            workspace_id=workspace_id,
            workflow_asset_id=workflow_id,
            workflow_version="1.0.0",
            workflow_definition_hash=spec.definition_hash,
            project_agent_deployment_id=deployment_id,
            pinned_agent_specs={"agentspec-recovery-1": {"version": "1.0.0", "definition_hash": "hash1"}},
        )
    )

    class ActiveDeploymentResolver:
        async def resolve_authority(self, ws, proj, dep):
            return {
                "state": "ACTIVE",
                "workspaceId": ws,
                "projectId": proj,
                "agentSpec": {"id": "agentspec-recovery-1", "version": "1.0.0", "definitionHash": "hash1"},
            }

    workflow_engine = WorkflowEngine(
        resolver=ActiveDeploymentResolver(), kernel=None, approval_service=approval_service
    )
    workflow_orchestration = WorkflowOrchestration(
        gateway=None,
        workflow_engine=workflow_engine,
        workflow_registry=None,
        approval_service=approval_service,
        workflow_definition_repository=workflow_definition_repository,
    )
    plane = SimpleNamespace(run_repository=run_repository, workflow_orchestration=workflow_orchestration)

    # 1. First (parent-process) execution pauses at the APPROVAL_GATE step.
    first = await execute_governed_workflow_run(plane, manifest)
    assert first.status == "waiting_approval"

    pending = await run_repository.list_pending_approvals(workspace_id=workspace_id)
    assert len(pending) == 1
    await approval_service.submit_decision(
        approval_id=pending[0].approval_id, reviewer="founder_user", approved=True
    )

    # Disconnect the parent engine (simulate worker shutdown) before resuming
    # in a completely separate process below.
    await engine.dispose()

    script_file = tmp_path / "run_governed_workflow_resume.py"
    script_file.write_text(_GOVERNED_WORKFLOW_RESUME_SUBPROCESS_SCRIPT)

    proc = subprocess.run(
        [sys.executable, str(script_file), TEST_DATABASE_URL, run_id],
        capture_output=True,
        text=True,
        check=False,
        env=dict(
            os.environ,
            PYTHONPATH=f"{Path.cwd()}:{Path.cwd() / 'packages'}:{Path.cwd() / 'apps'}",
        ),
    )
    assert proc.returncode == 0, f"Subprocess failed:\\nSTDOUT:\\n{proc.stdout}\\nSTDERR:\\n{proc.stderr}"
    assert "SUCCESS_GOVERNED_WORKFLOW_RESUME" in proc.stdout


@pytest.mark.asyncio
async def test_promotion_rejects_foreign_or_stale_subject_after_restart(tmp_path: Path) -> None:
    engine = create_async_engine(TEST_DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresRunRepository(session_factory)
    cand_store = PostgresSkillCandidateStore(session_factory)

    workspace_id = f"ws_rej_{uuid.uuid4().hex[:6]}"
    candidate_id = f"cand_rej_{uuid.uuid4().hex[:6]}"

    spec = SkillSpec(
        id=f"skill_{candidate_id}",
        version="1.0.0",
        name="Rejectable Skill",
        description="Testing rejection of stale subjects",
        instructions="Analyze safely.",
        required_capabilities=[],
    )
    cand = SkillCandidate(
        candidate_id=candidate_id,
        parent_run_id=f"run_{uuid.uuid4().hex[:6]}",
        proposed_skill=spec,
        eval_score=0.9,
        status=SkillStatus.EVALUATED,
    )
    saved = await cand_store.save_candidate(workspace_id, cand)

    approval_id = f"appr_stale_{uuid.uuid4().hex[:8]}"
    approval = RunApprovalRecord(
        approval_id=approval_id,
        workspace_id=workspace_id,
        binding_kind="CHANGE_REQUEST",
        run_id=None,
        action="promote_skill_candidate",
        subject_kind="skill_candidate",
        subject_ref=candidate_id,
        subject_hash=saved.definition_hash,
        requirement={"role": "founder"},
        status="pending",
    )
    await repo.create_approval(approval)
    await repo.decide_change_approval_and_enqueue(
        approval_id=approval_id,
        reviewer="founder_lead",
        approved=True,
    )

    await engine.dispose()

    # Launch subprocess to perform foreign workspace and stale subject verification
    script_file = tmp_path / "run_stale_rejection.py"
    script_file.write_text(_STALE_REJECTION_SUBPROCESS_SCRIPT)

    proc = subprocess.run(
        [
            sys.executable,
            str(script_file),
            TEST_DATABASE_URL,
            workspace_id,
            candidate_id,
            approval_id,
            saved.definition_hash,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=dict(
            os.environ,
            PYTHONPATH=f"{Path.cwd()}:{Path.cwd() / 'packages'}:{Path.cwd() / 'apps'}",
        ),
    )
    assert proc.returncode == 0, f"Subprocess failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    assert "SUCCESS_REJECTION_RECOVERY" in proc.stdout
