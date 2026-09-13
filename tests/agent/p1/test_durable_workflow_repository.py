from __future__ import annotations

import pytest

from agent.workflows.repository import InMemoryWorkflowDefinitionRepository
from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec


@pytest.mark.asyncio
async def test_durable_workflow_definition_repository():
    """Kiểm thử Durable Workflow Definition Repository (§10.3 & §43.2):
    Lưu trữ bất biến WorkflowSpec, nạp lại theo version và definition_hash.
    """
    repo = InMemoryWorkflowDefinitionRepository()

    spec_v1 = WorkflowSpec(
        id="wf_payout",
        version="1.0.0",
        description="Payout workflow v1",
        steps=[
            WorkflowStepSpec(
                id="step_validate",
                name="Validate Payout",
                step_type=StepType.DETERMINISTIC,
                handler="validate_fn",
            )
        ],
    )

    spec_v2 = WorkflowSpec(
        id="wf_payout",
        version="2.0.0",
        description="Payout workflow v2",
        steps=[
            WorkflowStepSpec(
                id="step_validate",
                name="Validate Payout",
                step_type=StepType.DETERMINISTIC,
                handler="validate_fn",
            ),
            WorkflowStepSpec(
                id="step_audit",
                name="Audit Log",
                step_type=StepType.DETERMINISTIC,
                handler="audit_fn",
            ),
        ],
    )

    rec1 = await repo.save_definition(spec_v1)
    rec2 = await repo.save_definition(spec_v2)

    assert rec1.definition_hash != rec2.definition_hash

    # Query by (id, version)
    fetched1 = await repo.get_definition("wf_payout", "1.0.0")
    assert fetched1 is not None
    assert fetched1.version == "1.0.0"
    assert len(fetched1.spec_data["steps"]) == 1

    # Query by definition_hash
    by_hash = await repo.get_by_hash(rec2.definition_hash)
    assert by_hash is not None
    assert by_hash.version == "2.0.0"

    # List all versions
    versions = await repo.list_versions("wf_payout")
    assert len(versions) == 2


@pytest.mark.asyncio
async def test_in_memory_repository_does_not_fallback_across_workspaces():
    repo = InMemoryWorkflowDefinitionRepository()
    spec = WorkflowSpec(
        id="wf_secret",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="step1",
                step_type=StepType.DETERMINISTIC,
                handler="test_fn",
            )
        ],
    )
    saved = await repo.save_definition(spec, workspace_id="tenant-A")

    # Asking for tenant-B must return None, NOT tenant-A's definition
    res_b = await repo.get_definition("wf_secret", "1.0.0", workspace_id="tenant-B")
    assert res_b is None

    # Asking for default workspace must return None
    res_default = await repo.get_definition("wf_secret", "1.0.0", workspace_id="default")
    assert res_default is None

    # Scoped get_by_hash with tenant-B must return None
    res_hash_b = await repo.get_by_hash(saved.definition_hash, workspace_id="tenant-B")
    assert res_hash_b is None

    # Scoped get_by_hash with tenant-A must return the record
    res_hash_a = await repo.get_by_hash(saved.definition_hash, workspace_id="tenant-A")
    assert res_hash_a is not None
    assert res_hash_a.workspace_id == "tenant-A"

