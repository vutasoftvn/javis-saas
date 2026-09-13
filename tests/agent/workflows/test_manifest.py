from __future__ import annotations

import os
import uuid
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent.workflows.manifest import (
    GovernedWorkflowRunManifest,
    InMemoryWorkflowManifestRepository,
    ManifestConflictError,
    PostgresWorkflowManifestRepository,
    StepRecordConflictError,
    WorkflowStepRecord,
    make_manifest,
)

_DB_URL = os.environ.get("AGENT_TEST_DATABASE_URL")
if not _DB_URL and os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.startswith("AGENT_TEST_DATABASE_URL="):
                _DB_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                break


@pytest.fixture
def postgres_repo():
    if not _DB_URL:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")
    engine = create_async_engine(_DB_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return PostgresWorkflowManifestRepository(session_factory)


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_type", ["in_memory", "postgres"])
async def test_manifest_is_insert_once_and_contains_project_scope(
    repo_type: str, postgres_repo
):
    repo = InMemoryWorkflowManifestRepository() if repo_type == "in_memory" else postgres_repo

    manifest = await repo.create_manifest(make_manifest(project_id="p-1"))
    assert manifest.project_id == "p-1"
    assert manifest.manifest_hash is not None

    with pytest.raises(ManifestConflictError):
        await repo.create_manifest(make_manifest(run_id=manifest.run_id, project_id="p-2"))


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_type", ["in_memory", "postgres"])
async def test_manifest_retrieval_by_run_id_and_hash(
    repo_type: str, postgres_repo
):
    repo = InMemoryWorkflowManifestRepository() if repo_type == "in_memory" else postgres_repo

    unique_proj = f"p-lookup-{uuid.uuid4().hex[:8]}"
    manifest = await repo.create_manifest(
        make_manifest(
            project_id=unique_proj,
            workflow_asset_id="wf_lookup_1",
            role_deployment_id="role_dep_123",
            project_agent_deployment_id="proj_agent_dep_456",
            pinned_agent_specs={"agent-1": "hash_agent_1"},
            pinned_skill_specs={"skill-1": "hash_skill_1"},
            capability_allowlist=["read_data", "write_log"],
            budget_limit={"max_tokens": 10000},
        )
    )

    by_run_id = await repo.get_manifest(manifest.run_id)
    assert by_run_id is not None
    assert by_run_id.run_id == manifest.run_id
    assert by_run_id.manifest_hash == manifest.manifest_hash
    assert by_run_id.role_deployment_id == "role_dep_123"
    assert by_run_id.pinned_agent_specs == {"agent-1": "hash_agent_1"}
    assert by_run_id.capability_allowlist == ["read_data", "write_log"]

    by_hash = await repo.get_manifest_by_hash(manifest.manifest_hash)
    assert by_hash is not None
    assert by_hash.run_id == manifest.run_id


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_type", ["in_memory", "postgres"])
async def test_step_records_lifecycle_and_conflict(
    repo_type: str, postgres_repo
):
    repo = InMemoryWorkflowManifestRepository() if repo_type == "in_memory" else postgres_repo
    run_id = f"run_{uuid.uuid4().hex[:12]}"

    step_1 = WorkflowStepRecord(
        run_id=run_id,
        step_id="step-extract",
        step_name="Extract Data",
        sequence_no=1,
        status="RUNNING",
        checkpoint_ref="ckpt_001",
        input_hash="hash_input_1",
    )
    saved_1 = await repo.create_step_record(step_1)
    assert saved_1.step_id == "step-extract"

    # Conflict on duplicate step_id for same run
    with pytest.raises(StepRecordConflictError):
        await repo.create_step_record(
            WorkflowStepRecord(
                run_id=run_id,
                step_id="step-extract",
                step_name="Extract Duplicate",
                sequence_no=2,
                status="RUNNING",
                input_hash="hash_input_2",
            )
        )

    step_2 = WorkflowStepRecord(
        run_id=run_id,
        step_id="step-transform",
        step_name="Transform Data",
        sequence_no=2,
        status="PENDING",
        input_hash="hash_input_2",
    )
    await repo.create_step_record(step_2)

    # Update step 1 to COMPLETED
    step_1.status = "COMPLETED"
    step_1.output_hash = "hash_output_1"
    step_1.safe_reason_code = "EXTRACT_OK"
    await repo.update_step_record(step_1)

    steps = await repo.get_step_records(run_id)
    assert len(steps) == 2
    assert steps[0].step_id == "step-extract"
    assert steps[0].status == "COMPLETED"
    assert steps[0].safe_reason_code == "EXTRACT_OK"
    assert steps[1].step_id == "step-transform"
    assert steps[1].status == "PENDING"
