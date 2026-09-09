from __future__ import annotations

from uuid import uuid4

import pytest
from agent.workforce.outcome_analysis import (
    OUTCOME_ANALYSIS_SKILL_ID,
    OUTCOME_ANALYST_CAPABILITY_REFS,
    resolve_outcome_analysis_binding,
)
from agent.workforce.repository import InMemoryWorkforceRepository


def test_capability_boundary_is_exactly_six_read_or_narrow_record() -> None:
    assert {
        "operations.task.read",
        "operations.task-result.read",
        "operations.work-package.read",
        "operations.evidence.read",
        "agent.artifact.read",
        "operations.outcome-assessment.record",
    } == OUTCOME_ANALYST_CAPABILITY_REFS
    assert "operations.task.advance" not in OUTCOME_ANALYST_CAPABILITY_REFS
    assert "operations.kr.actual.write" not in OUTCOME_ANALYST_CAPABILITY_REFS


@pytest.mark.asyncio
async def test_resolver_returns_the_exact_bound_employee_or_none() -> None:
    repo = InMemoryWorkforceRepository()
    emp_id = uuid4()
    asg_id = uuid4()

    # No binding yet -> None (fail closed, never a generic operations employee).
    assert await resolve_outcome_analysis_binding(repo, "ws_a", "tr_1", "TASK_OUTCOME") is None

    await repo.upsert_outcome_analysis_binding(
        workspace_id="ws_a",
        analysis_kind="TASK_OUTCOME",
        analyst_employee_id=emp_id,
        analyst_assignment_id=asg_id,
        policy="AUTO_ALL_TASKS",
        skill_id=OUTCOME_ANALYSIS_SKILL_ID,
        skill_version="1.0.0",
        definition_hash="sha256:skill",
        updated_by="founder_a",
    )

    binding = await resolve_outcome_analysis_binding(repo, "ws_a", "tr_1", "TASK_OUTCOME")
    assert binding is not None
    assert binding.agent_instance_id == str(emp_id)
    assert binding.assignment_id == str(asg_id)
    assert binding.skill_id == OUTCOME_ANALYSIS_SKILL_ID

    # Different workspace / kind is still None.
    assert await resolve_outcome_analysis_binding(repo, "ws_b", "tr_1", "TASK_OUTCOME") is None
    assert (
        await resolve_outcome_analysis_binding(repo, "ws_a", "tr_1", "PROJECT_OUTCOME_SYNTHESIS")
        is None
    )


@pytest.mark.asyncio
async def test_resolver_rejects_a_binding_pinned_to_the_wrong_skill() -> None:
    repo = InMemoryWorkforceRepository()
    await repo.upsert_outcome_analysis_binding(
        workspace_id="ws_a",
        analysis_kind="TASK_OUTCOME",
        analyst_employee_id=uuid4(),
        analyst_assignment_id=uuid4(),
        policy="AUTO_ALL_TASKS",
        skill_id="operations/some-other-skill",
        skill_version="1.0.0",
        definition_hash="sha256:x",
        updated_by="founder_a",
    )
    assert await resolve_outcome_analysis_binding(repo, "ws_a", "tr_1", "TASK_OUTCOME") is None


@pytest.mark.asyncio
async def test_upsert_bumps_version() -> None:
    repo = InMemoryWorkforceRepository()
    b1 = await repo.upsert_outcome_analysis_binding(
        "ws_a",
        "TASK_OUTCOME",
        uuid4(),
        uuid4(),
        "AUTO_ALL_TASKS",
        OUTCOME_ANALYSIS_SKILL_ID,
        "1.0.0",
        "sha256:a",
        "founder_a",
    )
    b2 = await repo.upsert_outcome_analysis_binding(
        "ws_a",
        "TASK_OUTCOME",
        uuid4(),
        uuid4(),
        "MANUAL",
        OUTCOME_ANALYSIS_SKILL_ID,
        "1.1.0",
        "sha256:b",
        "founder_a",
    )
    assert b1.version == 1
    assert b2.version == 2
    assert b2.policy == "MANUAL"
