from __future__ import annotations

from agent_core.evals.promotion import PromotionEvidence
from agent_core.evals.promotion_gate import PromotionGate
from agent_core.governance.contracts import PinnedSpecIdentity


def _target_ref() -> PinnedSpecIdentity:
    return PinnedSpecIdentity(spec_kind="agent", spec_id="cofounder", spec_version="17", definition_hash="a" * 64)


def _valid_evidence() -> PromotionEvidence:
    return PromotionEvidence(
        target_ref=_target_ref(),
        required_eval_run_ids=["evalrun_1"],
        observed_fingerprints={"cofounder": "a" * 64},
        policy_version="1",
        policy_checks_passed=True,
    )


def test_promotion_gate_approves_valid_fresh_evidence():
    gate = PromotionGate(policy_version="1")

    result = gate.check(_valid_evidence(), current_fingerprints={"cofounder": "a" * 64})

    assert result.approved is True
    assert result.blocking_issues == []


def test_promotion_gate_rejects_stale_evidence():
    gate = PromotionGate(policy_version="1")

    result = gate.check(_valid_evidence(), current_fingerprints={"cofounder": "c" * 64})

    assert result.approved is False
    assert any("stale" in issue.lower() for issue in result.blocking_issues)


def test_promotion_gate_rejects_when_policy_checks_not_passed():
    evidence = _valid_evidence().model_copy(update={"policy_checks_passed": False})
    gate = PromotionGate(policy_version="1")

    result = gate.check(evidence, current_fingerprints={"cofounder": "a" * 64})

    assert result.approved is False
    assert any("chưa pass" in issue for issue in result.blocking_issues)


def test_promotion_gate_rejects_when_no_eval_run_ids():
    evidence = _valid_evidence().model_copy(update={"required_eval_run_ids": []})
    gate = PromotionGate(policy_version="1")

    result = gate.check(evidence, current_fingerprints={"cofounder": "a" * 64})

    assert result.approved is False


def test_promotion_gate_rejects_when_policy_version_mismatches():
    gate = PromotionGate(policy_version="2")

    result = gate.check(_valid_evidence(), current_fingerprints={"cofounder": "a" * 64})

    assert result.approved is False
    assert any("policy_version" in issue for issue in result.blocking_issues)


def test_promotion_gate_result_carries_target_ref_and_evidence_id():
    evidence = _valid_evidence()
    gate = PromotionGate(policy_version="1")

    result = gate.check(evidence, current_fingerprints={"cofounder": "a" * 64})

    assert result.target_ref == evidence.target_ref
    assert result.evidence_id == evidence.evidence_id
