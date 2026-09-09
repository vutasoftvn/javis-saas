from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from agent.workforce.delegation import (
    FounderApprovalRequired,
    InMemoryWorkforceDelegationRepository,
    require_founder_or_delegate,
)
from agent.workforce.scorecard import (
    EmployeeScorecard,
    ReviewedAttemptOutcome,
    get_employee_scorecard,
)

START = datetime(2026, 9, 1, tzinfo=UTC)
END = datetime(2026, 9, 30, tzinfo=UTC)


class _Evidence:
    def __init__(self, outcomes: list[ReviewedAttemptOutcome] | None) -> None:
        self._outcomes = outcomes

    async def reviewed_attempt_outcomes(self, ws, emp, ws_start, ws_end):
        return self._outcomes


class _StubFounder:
    def __init__(self, founders: set[tuple[str, str]]) -> None:
        self._founders = founders

    async def is_founder(self, workspace_id: str, principal_id: str) -> bool:
        return (workspace_id, principal_id) in self._founders


@pytest.mark.asyncio
async def test_scorecard_counts_only_reviewed_attempt_outcomes() -> None:
    # No review yet -> no business score.
    empty = await get_employee_scorecard(
        evidence=_Evidence([]),
        workspace_id="ws_a",
        agent_instance_id="emp_1",
        window_start=START,
        window_end=END,
    )
    assert empty.available is True
    assert empty.accepted_count == 0

    reviewed = await get_employee_scorecard(
        evidence=_Evidence(
            [
                ReviewedAttemptOutcome("emp_1", "sha256:v1", "BAU", "analysis", "ACCEPT"),
                ReviewedAttemptOutcome("emp_1", "sha256:v1", "BAU", "analysis", "REWORK", retry_count=1),
                ReviewedAttemptOutcome("emp_1", "sha256:v2", "DIRECT_KR", "delivery", "ACCEPT", escalated=True),
            ]
        ),
        workspace_id="ws_a",
        agent_instance_id="emp_1",
        window_start=START,
        window_end=END,
    )
    assert reviewed.accepted_count == 2
    assert reviewed.rework_count == 1
    assert reviewed.escalation_count == 1
    assert reviewed.retry_count == 1
    assert reviewed.accepted_by_spec == {"sha256:v1": 1, "sha256:v2": 1}


@pytest.mark.asyncio
async def test_scorecard_unavailable_when_company_evidence_missing_not_zero() -> None:
    card = await get_employee_scorecard(
        evidence=_Evidence(None),
        workspace_id="ws_a",
        agent_instance_id="emp_1",
        window_start=START,
        window_end=END,
    )
    assert isinstance(card, EmployeeScorecard)
    assert card.available is False
    assert card.unavailable_reason == "company_evidence_unavailable"


@pytest.mark.asyncio
async def test_require_founder_or_delegate_paths() -> None:
    repo = InMemoryWorkforceDelegationRepository()
    founder = _StubFounder({("ws_a", "founder_1")})

    # Founder always passes.
    await require_founder_or_delegate(
        repository=repo,
        founder_check=founder,
        workspace_id="ws_a",
        principal_id="founder_1",
        action="queue_control",
        functional_key=None,
    )

    # Non-founder, no delegation -> raises.
    with pytest.raises(FounderApprovalRequired):
        await require_founder_or_delegate(
            repository=repo,
            founder_check=founder,
            workspace_id="ws_a",
            principal_id="mgr_1",
            action="queue_control",
            functional_key="operations",
        )

    # Grant a scoped delegation -> passes for the matching key.
    await repo.grant_delegation("ws_a", "founder_1", "mgr_1", "queue_control", "operations", None)
    await require_founder_or_delegate(
        repository=repo,
        founder_check=founder,
        workspace_id="ws_a",
        principal_id="mgr_1",
        action="queue_control",
        functional_key="operations",
    )

    # Wrong functional key -> still raises.
    with pytest.raises(FounderApprovalRequired):
        await require_founder_or_delegate(
            repository=repo,
            founder_check=founder,
            workspace_id="ws_a",
            principal_id="mgr_1",
            action="queue_control",
            functional_key="finance",
        )


@pytest.mark.asyncio
async def test_expired_and_revoked_delegation_is_denied() -> None:
    repo = InMemoryWorkforceDelegationRepository()
    founder = _StubFounder(set())

    expired = await repo.grant_delegation(
        "ws_a", "founder_1", "mgr_1", "review_override", None,
        datetime.now(UTC) - timedelta(hours=1),
    )
    assert expired.is_effective() is False
    with pytest.raises(FounderApprovalRequired):
        await require_founder_or_delegate(
            repository=repo,
            founder_check=founder,
            workspace_id="ws_a",
            principal_id="mgr_1",
            action="review_override",
            functional_key=None,
        )

    active = await repo.grant_delegation("ws_a", "founder_1", "mgr_2", "review_override", None, None)
    await require_founder_or_delegate(
        repository=repo,
        founder_check=founder,
        workspace_id="ws_a",
        principal_id="mgr_2",
        action="review_override",
        functional_key=None,
    )
    await repo.revoke_delegation("ws_a", active.delegation_id, "founder_1")
    with pytest.raises(FounderApprovalRequired):
        await require_founder_or_delegate(
            repository=repo,
            founder_check=founder,
            workspace_id="ws_a",
            principal_id="mgr_2",
            action="review_override",
            functional_key=None,
        )
