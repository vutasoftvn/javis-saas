from __future__ import annotations

from uuid import uuid4

import pytest

from agent.workforce.models import WorkforceAssignmentRecord
from agent.workforce.repository import InMemoryWorkforceRepository


@pytest.mark.asyncio
async def test_workforce_assignment_model_and_in_memory_binding() -> None:
    repo = InMemoryWorkforceRepository()
    workspace_id = "ws_test_101"

    # Create assignment with company_workforce_member_id
    assignment = await repo.create_assignment(
        workspace_id=workspace_id,
        functional_key="operations",
        spec_id="cosa.agents.operations",
        spec_version="1.0.0",
        definition_hash="sha256:ops",
        configured_by="user:founder_1",
        company_workforce_member_id="999001",
    )

    assert assignment.company_workforce_member_id == "999001"

    # Fetch assignment
    fetched = await repo.get_assignment(workspace_id, assignment.assignment_id)
    assert fetched is not None
    assert fetched.company_workforce_member_id == "999001"

    # List assignments
    assignments = await repo.list_assignments(workspace_id)
    assert len(assignments) == 1
    assert assignments[0].company_workforce_member_id == "999001"

    # Retire assignment preserves company_workforce_member_id
    retired = await repo.retire_assignment(workspace_id, assignment.assignment_id)
    assert retired is not None
    assert retired.status == "RETIRED"
    assert retired.company_workforce_member_id == "999001"


@pytest.mark.asyncio
async def test_assignment_conflict_update_preserves_or_updates_company_workforce_member_id() -> None:
    repo = InMemoryWorkforceRepository()
    workspace_id = "ws_test_102"

    first = await repo.create_assignment(
        workspace_id=workspace_id,
        functional_key="operations",
        spec_id="cosa.agents.operations",
        spec_version="1.0.0",
        definition_hash="sha256:ops",
        configured_by="user:founder_1",
        company_workforce_member_id="999001",
    )
    assert first.company_workforce_member_id == "999001"

    second = await repo.create_assignment(
        workspace_id=workspace_id,
        functional_key="operations",
        spec_id="cosa.agents.operations",
        spec_version="1.0.0",
        definition_hash="sha256:ops",
        configured_by="user:founder_1",
        company_workforce_member_id="999002",
    )
    assert second.assignment_id == first.assignment_id
    assert second.company_workforce_member_id == "999002"
