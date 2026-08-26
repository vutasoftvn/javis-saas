from __future__ import annotations

from agent_core.evals.promotion import PromotionEvidence
from agent_core.governance.contracts import PinnedSpecIdentity


def _target_ref() -> PinnedSpecIdentity:
    return PinnedSpecIdentity(spec_kind="agent", spec_id="cofounder", spec_version="17", definition_hash="a" * 64)


def test_promotion_evidence_has_sensible_defaults():
    evidence = PromotionEvidence(target_ref=_target_ref(), policy_version="1", policy_checks_passed=True)

    assert evidence.required_eval_run_ids == []
    assert evidence.observed_fingerprints == {}
    assert evidence.check_details == {}
    assert evidence.evidence_id.startswith("promoevid_")


def test_promotion_evidence_two_instances_get_distinct_ids():
    a = PromotionEvidence(target_ref=_target_ref(), policy_version="1", policy_checks_passed=True)
    b = PromotionEvidence(target_ref=_target_ref(), policy_version="1", policy_checks_passed=True)

    assert a.evidence_id != b.evidence_id


def test_is_stale_returns_false_when_all_fingerprints_match():
    evidence = PromotionEvidence(
        target_ref=_target_ref(),
        policy_version="1",
        policy_checks_passed=True,
        observed_fingerprints={"cofounder": "a" * 64, "cofounder/system": "b" * 64},
    )

    assert evidence.is_stale({"cofounder": "a" * 64, "cofounder/system": "b" * 64}) is False


def test_is_stale_returns_true_when_target_fingerprint_changed():
    evidence = PromotionEvidence(
        target_ref=_target_ref(),
        policy_version="1",
        policy_checks_passed=True,
        observed_fingerprints={"cofounder": "a" * 64},
    )

    assert evidence.is_stale({"cofounder": "c" * 64}) is True


def test_is_stale_returns_true_when_dependency_fingerprint_changed():
    evidence = PromotionEvidence(
        target_ref=_target_ref(),
        policy_version="1",
        policy_checks_passed=True,
        observed_fingerprints={"cofounder": "a" * 64, "cofounder/system": "b" * 64},
    )

    assert evidence.is_stale({"cofounder": "a" * 64, "cofounder/system": "c" * 64}) is True


def test_is_stale_returns_true_when_observed_name_missing_from_current():
    evidence = PromotionEvidence(
        target_ref=_target_ref(),
        policy_version="1",
        policy_checks_passed=True,
        observed_fingerprints={"cofounder": "a" * 64, "cofounder/system": "b" * 64},
    )

    assert evidence.is_stale({"cofounder": "a" * 64}) is True
