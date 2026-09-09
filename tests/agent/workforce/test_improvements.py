from __future__ import annotations

from uuid import uuid4

import pytest
from agent.workforce.improvements import (
    ForbiddenProposalField,
    FounderApprovalRequired,
    InMemoryImprovementProposalRepository,
    approve_canary,
    create_proposal,
    promote_proposal,
    rollback,
)


@pytest.mark.asyncio
async def test_evaluation_owner_can_propose_but_not_activate_capability_change() -> None:
    repo = InMemoryImprovementProposalRepository()
    emp = uuid4()
    proposal = await create_proposal(
        repository=repo,
        workspace_id="ws_a",
        agent_instance_id=emp,
        created_by="eval_owner",
        change_class="capability",
        hypothesis="needs a write capability",
        proposed_revision={"add_capability": "operations.task.advance"},
        baseline_definition_hash="sha256:baseline",
    )
    assert proposal.status == "DRAFT"
    assert proposal.requires_founder is True

    # Evaluation owner submits -> goes to PENDING_FOUNDER_REVIEW, not APPROVED.
    submitted = await promote_proposal(
        repository=repo,
        workspace_id="ws_a",
        proposal_id=proposal.proposal_id,
        actor_id="eval_owner",
        is_founder=False,
    )
    assert submitted.status == "PENDING_FOUNDER_REVIEW"

    # Evaluation owner cannot approve it.
    with pytest.raises(FounderApprovalRequired):
        await promote_proposal(
            repository=repo,
            workspace_id="ws_a",
            proposal_id=proposal.proposal_id,
            actor_id="eval_owner",
            is_founder=False,
        )

    # Founder can.
    approved = await promote_proposal(
        repository=repo,
        workspace_id="ws_a",
        proposal_id=proposal.proposal_id,
        actor_id="founder_1",
        is_founder=True,
    )
    assert approved.status == "APPROVED"


@pytest.mark.asyncio
async def test_rubric_change_is_self_service_for_evaluation_owner() -> None:
    repo = InMemoryImprovementProposalRepository()
    proposal = await create_proposal(
        repository=repo,
        workspace_id="ws_a",
        agent_instance_id=uuid4(),
        created_by="eval_owner",
        change_class="rubric",
        hypothesis="tighten correctness weighting",
        proposed_revision={"rubric": {"correctness": 6}},
    )
    assert proposal.requires_founder is False
    promoted = await promote_proposal(
        repository=repo,
        workspace_id="ws_a",
        proposal_id=proposal.proposal_id,
        actor_id="eval_owner",
        is_founder=False,
    )
    assert promoted.status == "APPROVED"


@pytest.mark.asyncio
async def test_canary_pins_candidate_and_rollback_preserves_baseline() -> None:
    repo = InMemoryImprovementProposalRepository()
    proposal = await create_proposal(
        repository=repo,
        workspace_id="ws_a",
        agent_instance_id=uuid4(),
        created_by="eval_owner",
        change_class="autonomy",
        hypothesis="raise autonomy ceiling",
        proposed_revision={"autonomy_ceiling": "L2_ACT"},
        baseline_definition_hash="sha256:baseline",
        rollback_plan="revert to baseline assignment",
    )
    canary = await approve_canary(
        repository=repo,
        workspace_id="ws_a",
        proposal_id=proposal.proposal_id,
        founder_id="founder_1",
        candidate_definition_hash="sha256:candidate",
        selected_attempt_ids=["wa_1", "wa_2"],
    )
    assert canary.status == "CANARY"
    assert canary.candidate_definition_hash == "sha256:candidate"
    assert canary.canary_selection == {"attempt_ids": ["wa_1", "wa_2"]}

    rolled = await rollback(
        repository=repo,
        workspace_id="ws_a",
        proposal_id=proposal.proposal_id,
        founder_id="founder_1",
    )
    assert rolled.status == "ROLLED_BACK"
    # Baseline still available; evidence not deleted.
    assert rolled.baseline_definition_hash == "sha256:baseline"
    assert "canary_started" in [e[1] for e in repo.events]
    assert "rolled_back" in [e[1] for e in repo.events]


@pytest.mark.asyncio
async def test_rejects_credential_or_prompt_secret_fields() -> None:
    repo = InMemoryImprovementProposalRepository()
    with pytest.raises(ForbiddenProposalField):
        await create_proposal(
            repository=repo,
            workspace_id="ws_a",
            agent_instance_id=uuid4(),
            created_by="eval_owner",
            change_class="rubric",
            hypothesis="x",
            proposed_revision={"api_key": "sk-123"},
        )
