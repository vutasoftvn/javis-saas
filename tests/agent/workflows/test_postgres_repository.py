from __future__ import annotations

import os
import uuid
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent.workflows.postgres_repository import PostgresWorkflowDefinitionRepository
from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec

_DB_URL = os.environ.get("AGENT_TEST_DATABASE_URL")
if not _DB_URL and os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.startswith("AGENT_TEST_DATABASE_URL="):
                _DB_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                break


def _make_workflow_spec(
    workflow_id: str | None = None, version: str = "1.0.0"
) -> WorkflowSpec:
    wid = workflow_id or f"wf_{uuid.uuid4().hex[:8]}"
    return WorkflowSpec(
        id=wid,
        name=f"Workflow {wid}",
        description="Test workflow for persistence",
        version=version,
        steps=[
            WorkflowStepSpec(
                id="step-1",
                name="First Step",
                type=StepType.TOOL_CALL,
                tool="test_tool",
                inputs={"param": "value"},
            ),
            WorkflowStepSpec(
                id="step-2",
                name="Second Step",
                type=StepType.DETERMINISTIC,
                depends_on=["step-1"],
            ),
        ],
    ).with_hash()


@pytest.fixture
def factory():
    if not _DB_URL:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")
    engine = create_async_engine(_DB_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return session_factory


@pytest.mark.asyncio
async def test_postgres_workflow_definition_survives_repository_restart(factory):
    first = PostgresWorkflowDefinitionRepository(factory)
    spec = _make_workflow_spec()
    saved = await first.save_definition(spec, workspace_id="ws-test-1")
    assert saved.definition_hash == spec.definition_hash

    # Simulate restart with new repo instance
    second = PostgresWorkflowDefinitionRepository(factory)
    loaded = await second.get_by_hash(saved.definition_hash)
    assert loaded is not None
    assert loaded.workflow_id == spec.id
    assert loaded.version == spec.version
    assert loaded.definition_hash == spec.definition_hash
    assert loaded.spec_data == saved.spec_data


@pytest.mark.asyncio
async def test_save_and_get_definition_by_id_and_version(factory):
    repo = PostgresWorkflowDefinitionRepository(factory)
    spec_v1 = _make_workflow_spec(version="1.0.0")
    await repo.save_definition(spec_v1, workspace_id="ws-test-multi")

    loaded_v1 = await repo.get_definition(spec_v1.id, "1.0.0", workspace_id="ws-test-multi")
    assert loaded_v1 is not None
    assert loaded_v1.definition_hash == spec_v1.definition_hash

    # Non-existent version returns None
    missing = await repo.get_definition(spec_v1.id, "9.9.9", workspace_id="ws-test-multi")
    assert missing is None


@pytest.mark.asyncio
async def test_list_versions(factory):
    repo = PostgresWorkflowDefinitionRepository(factory)
    wid = f"wf_{uuid.uuid4().hex[:8]}"

    spec_v1 = _make_workflow_spec(workflow_id=wid, version="1.0.0")
    spec_v2 = _make_workflow_spec(workflow_id=wid, version="1.1.0")

    await repo.save_definition(spec_v1, workspace_id="ws-versions")
    await repo.save_definition(spec_v2, workspace_id="ws-versions")

    versions = await repo.list_versions(wid, workspace_id="ws-versions")
    assert len(versions) == 2
    assert {v.version for v in versions} == {"1.0.0", "1.1.0"}


@pytest.mark.asyncio
async def test_rejects_mutation_of_published_version_with_different_hash(factory):
    repo = PostgresWorkflowDefinitionRepository(factory)
    spec = _make_workflow_spec()
    await repo.save_definition(spec, workspace_id="ws-immut")

    # Attempt to mutate published version
    mutated = WorkflowSpec(
        id=spec.id,
        name="Mutated Name",
        description="Different description",
        version=spec.version,
        steps=[
            WorkflowStepSpec(
                id="step-other",
                type=StepType.TOOL_CALL,
                tool="other_tool",
            )
        ],
    ).with_hash()

    with pytest.raises(ValueError, match="Cannot mutate published workflow"):
        await repo.save_definition(mutated, workspace_id="ws-immut")
