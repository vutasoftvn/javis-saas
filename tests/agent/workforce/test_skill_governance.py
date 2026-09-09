from __future__ import annotations

from uuid import uuid4

import pytest
from agent.workforce.outcome_analysis import OUTCOME_ANALYSIS_SKILL_ID
from agent.workforce.skill_governance import (
    FounderApprovalRequired,
    InMemorySkillGovernanceRepository,
    InvalidCapabilityBoundary,
    PolicyValidationError,
    StalePolicyDraft,
    create_policy_draft,
    create_skill_change_draft,
    publish_outcome_analysis_policy,
    rollback_outcome_analysis_policy,
)


class _Validators:
    def __init__(self, founders: set[str], active=True, effective=True, published=True) -> None:
        self.founders = founders
        self.active = active
        self.effective = effective
        self.published = published

    async def is_founder(self, workspace_id: str, principal_id: str) -> bool:
        return principal_id in self.founders

    async def employee_is_active(self, workspace_id, employee_id) -> bool:
        return self.active

    async def assignment_is_effective(self, workspace_id, assignment_id) -> bool:
        return self.effective

    async def skill_version_is_published(self, skill_id, skill_version) -> bool:
        return self.published


def _payload(emp, asg):
    return {
        "policy": "AUTO_ALL_TASKS",
        "analyst_employee_id": str(emp),
        "analyst_assignment_id": str(asg),
    }


@pytest.mark.asyncio
async def test_founder_publish_binds_exact_active_employee_assignment_and_pinned_skill() -> None:
    repo = InMemorySkillGovernanceRepository()
    validators = _Validators(founders={"founder_1"})
    emp, asg = uuid4(), uuid4()

    draft = await create_policy_draft(
        repository=repo, workspace_id="ws_a", created_by="founder_1", payload=_payload(emp, asg)
    )
    published = await publish_outcome_analysis_policy(
        repository=repo,
        validators=validators,
        workspace_id="ws_a",
        draft_id=draft.draft_id,
        expected_version=draft.version,
        actor_id="founder_1",
    )
    assert published.analyst_employee_id == emp
    assert published.analyst_assignment_id == asg
    assert published.skill_id == OUTCOME_ANALYSIS_SKILL_ID
    assert published.version_no == 1
    assert (repo.events[-1][1], repo.events[-1][2]) == ("published", "founder_1")


@pytest.mark.asyncio
async def test_manager_cannot_publish_or_add_write_capability_to_outcome_skill() -> None:
    repo = InMemorySkillGovernanceRepository()
    validators = _Validators(founders={"founder_1"})
    emp, asg = uuid4(), uuid4()

    draft = await create_policy_draft(
        repository=repo, workspace_id="ws_a", created_by="founder_1", payload=_payload(emp, asg)
    )
    with pytest.raises(FounderApprovalRequired):
        await publish_outcome_analysis_policy(
            repository=repo,
            validators=validators,
            workspace_id="ws_a",
            draft_id=draft.draft_id,
            expected_version=draft.version,
            actor_id="manager_1",
        )

    with pytest.raises(InvalidCapabilityBoundary):
        await create_skill_change_draft(
            repository=repo,
            workspace_id="ws_a",
            created_by="founder_1",
            change={
                "add_capability": "operations.task.advance",
                "analyst_employee_id": str(emp),
                "analyst_assignment_id": str(asg),
            },
        )


@pytest.mark.asyncio
async def test_publish_fails_closed_when_employee_or_skill_not_ready() -> None:
    repo = InMemorySkillGovernanceRepository()
    emp, asg = uuid4(), uuid4()
    draft = await create_policy_draft(
        repository=repo, workspace_id="ws_a", created_by="founder_1", payload=_payload(emp, asg)
    )
    for bad in (
        _Validators(founders={"founder_1"}, active=False),
        _Validators(founders={"founder_1"}, effective=False),
        _Validators(founders={"founder_1"}, published=False),
    ):
        with pytest.raises(PolicyValidationError):
            await publish_outcome_analysis_policy(
                repository=repo,
                validators=bad,
                workspace_id="ws_a",
                draft_id=draft.draft_id,
                expected_version=draft.version,
                actor_id="founder_1",
            )


@pytest.mark.asyncio
async def test_stale_draft_version_is_rejected() -> None:
    repo = InMemorySkillGovernanceRepository()
    validators = _Validators(founders={"founder_1"})
    emp, asg = uuid4(), uuid4()
    draft = await create_policy_draft(
        repository=repo, workspace_id="ws_a", created_by="founder_1", payload=_payload(emp, asg)
    )
    with pytest.raises(StalePolicyDraft):
        await publish_outcome_analysis_policy(
            repository=repo,
            validators=validators,
            workspace_id="ws_a",
            draft_id=draft.draft_id,
            expected_version=999,
            actor_id="founder_1",
        )


@pytest.mark.asyncio
async def test_rollback_creates_a_new_version_pointing_at_the_target() -> None:
    repo = InMemorySkillGovernanceRepository()
    validators = _Validators(founders={"founder_1"})
    emp, asg = uuid4(), uuid4()
    draft = await create_policy_draft(
        repository=repo, workspace_id="ws_a", created_by="founder_1", payload=_payload(emp, asg)
    )
    v1 = await publish_outcome_analysis_policy(
        repository=repo,
        validators=validators,
        workspace_id="ws_a",
        draft_id=draft.draft_id,
        expected_version=draft.version,
        actor_id="founder_1",
    )
    rolled = await rollback_outcome_analysis_policy(
        repository=repo,
        validators=validators,
        workspace_id="ws_a",
        target_version_id=v1.policy_version_id,
        actor_id="founder_1",
    )
    assert rolled.version_no == 2
    assert rolled.rollback_target_version_id == v1.policy_version_id
    # Historical version untouched.
    assert repo.versions[0].policy_version_id == v1.policy_version_id
