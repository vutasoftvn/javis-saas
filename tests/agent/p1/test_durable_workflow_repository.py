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
