from __future__ import annotations

from agent_core.governance.contracts import PinnedSpecIdentity, SpecResolutionManifest


def _identity(spec_id: str = "cofounder", version: str = "1") -> PinnedSpecIdentity:
    return PinnedSpecIdentity(
        spec_kind="agent",
        spec_id=spec_id,
        spec_version=version,
        definition_hash="a" * 64,
    )


def test_pinned_spec_identity_holds_the_four_required_fields():
    identity = _identity()

    assert identity.spec_kind == "agent"
    assert identity.spec_id == "cofounder"
    assert identity.spec_version == "1"
    assert identity.definition_hash == "a" * 64


def test_spec_resolution_manifest_starts_empty():
    manifest = SpecResolutionManifest()

    assert manifest.entries == ()


def test_with_entry_appends_a_new_pinned_identity():
    manifest = SpecResolutionManifest()
    entry = _identity()

    updated = manifest.with_entry(entry)

    assert updated.entries == (entry,)
    assert manifest.entries == ()  # bản gốc không bị mutate


def test_with_entry_never_drops_an_earlier_entry():
    first = _identity(spec_id="supervisor")
    second = _identity(spec_id="legal")  # vd: delegate động, resolve giữa chừng Run

    manifest = SpecResolutionManifest().with_entry(first).with_entry(second)

    assert manifest.entries == (first, second)


def test_with_entry_is_idempotent_for_the_same_identity():
    entry = _identity()
    manifest = SpecResolutionManifest().with_entry(entry)

    manifest_again = manifest.with_entry(entry)

    assert manifest_again.entries == (entry,)


from agent_core.governance.contracts import (
    AllOf,
    AnyOf,
    ApprovalEvidence,
    PolicyDecision,
    PolicyOutcome,
    Quorum,
    RoleApproval,
    UserApproval,
)


def test_policy_outcome_has_the_expected_values():
    assert {o.value for o in PolicyOutcome} == {"ALLOW", "DENY", "REQUIRE_APPROVAL", "NON_APPROVABLE"}


def test_role_approval_predicate_holds_a_role():
    predicate = RoleApproval(role="founder")

    assert predicate.role == "founder"
    assert predicate.kind == "role_approval"


def test_user_approval_predicate_holds_a_user_id():
    predicate = UserApproval(user_id="alice")

    assert predicate.user_id == "alice"
    assert predicate.kind == "user_approval"


def test_all_of_wraps_multiple_predicates():
    predicate = AllOf(predicates=(RoleApproval(role="founder"), RoleApproval(role="cfo")))

    assert len(predicate.predicates) == 2
    assert predicate.kind == "all"


def test_any_of_wraps_multiple_predicates():
    predicate = AnyOf(predicates=(RoleApproval(role="security"), UserApproval(user_id="alice")))

    assert len(predicate.predicates) == 2
    assert predicate.kind == "any"


def test_quorum_holds_a_count_and_eligible_roles():
    predicate = Quorum(count=2, roles=("cfo", "coo", "finance_admin"))

    assert predicate.count == 2
    assert predicate.roles == ("cfo", "coo", "finance_admin")


def test_policy_decision_defaults_to_no_requirement_and_no_reasons():
    decision = PolicyDecision(outcome=PolicyOutcome.ALLOW)

    assert decision.requirement is None
    assert decision.reasons == ()


def test_policy_decision_can_hold_a_composite_requirement():
    requirement = AllOf(predicates=(RoleApproval(role="founder"), RoleApproval(role="finance_admin")))

    decision = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        requirement=requirement,
        reasons=("tool_risk=CRITICAL",),
    )

    assert decision.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert decision.requirement == requirement
    assert decision.reasons == ("tool_risk=CRITICAL",)


def test_approval_evidence_holds_approver_scope_and_validity_window():
    evidence = ApprovalEvidence(
        approver="founder-1",
        scope="tool_call_42",
        decided_at="2026-08-23T10:00:00Z",
        valid_until=None,
    )

    assert evidence.approver == "founder-1"
    assert evidence.scope == "tool_call_42"
    assert evidence.valid_until is None


def test_approval_evidence_generates_a_uuid_id_by_default():
    evidence = ApprovalEvidence(approver="founder-1", scope="tool_call_42", decided_at="2026-08-23T10:00:00Z")

    assert evidence.id
    assert isinstance(evidence.id, str)


def test_approval_evidence_accepts_an_explicit_id():
    evidence = ApprovalEvidence(
        id="evidence-fixed-1",
        approver="founder-1",
        scope="tool_call_42",
        decided_at="2026-08-23T10:00:00Z",
    )

    assert evidence.id == "evidence-fixed-1"


import pytest
from pydantic import ValidationError


def test_pinned_spec_identity_accepts_prompt_kind():
    identity = PinnedSpecIdentity(spec_kind="prompt", spec_id="cofounder/system", spec_version="2026.08.3", definition_hash="a" * 64)
    assert identity.spec_kind == "prompt"


def test_pinned_spec_identity_accepts_model_policy_kind():
    identity = PinnedSpecIdentity(spec_kind="model_policy", spec_id="default-deepseek", spec_version="7", definition_hash="a" * 64)
    assert identity.spec_kind == "model_policy"


def test_pinned_spec_identity_accepts_tool_contract_kind():
    identity = PinnedSpecIdentity(spec_kind="tool_contract", spec_id="company.strategy.read", spec_version="3", definition_hash="a" * 64)
    assert identity.spec_kind == "tool_contract"


def test_pinned_spec_identity_accepts_skill_kind():
    identity = PinnedSpecIdentity(spec_kind="skill", spec_id="research", spec_version="12", definition_hash="a" * 64)
    assert identity.spec_kind == "skill"


def test_pinned_spec_identity_still_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        PinnedSpecIdentity(spec_kind="unknown", spec_id="x", spec_version="1", definition_hash="a" * 64)


def test_pinned_spec_identity_accepts_eval_suite_kind():
    identity = PinnedSpecIdentity(
        spec_kind="eval_suite", spec_id="cofounder-core", spec_version="24", definition_hash="a" * 64
    )
    assert identity.spec_kind == "eval_suite"
