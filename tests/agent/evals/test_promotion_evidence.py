from __future__ import annotations

from agent.evals.promotion import PromotionEvidence
from agent.governance.contracts import PinnedSpecIdentity


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


from agent.evals.artifacts import EvalRun
from agent.evals.promotion import build_promotion_evidence
from agent.governance.contracts import SpecDependencyEdge


def test_build_promotion_evidence_includes_target_and_dependency_fingerprints():
    target_ref = _target_ref()
    dep_ref = PinnedSpecIdentity(
        spec_kind="prompt", spec_id="cofounder/system", spec_version="1", definition_hash="b" * 64
    )
    edge = SpecDependencyEdge(owner=target_ref, dependency=dep_ref, relation="uses_prompt")
    run = EvalRun(target_ref=target_ref, status="completed", pass_rate=1.0)

    evidence = build_promotion_evidence(
        target_ref=target_ref,
        dependency_edges=(edge,),
        eval_runs=[run],
        policy_version="1",
        pass_rate_threshold=0.8,
    )

    assert evidence.observed_fingerprints["cofounder"] == "a" * 64
    assert evidence.observed_fingerprints["cofounder/system"] == "b" * 64
    assert evidence.required_eval_run_ids == [run.run_id]


def test_build_promotion_evidence_passes_when_all_runs_completed_above_threshold():
    target_ref = _target_ref()
    run = EvalRun(target_ref=target_ref, status="completed", pass_rate=0.95)

    evidence = build_promotion_evidence(
        target_ref=target_ref, eval_runs=[run], policy_version="1", pass_rate_threshold=0.8
    )

    assert evidence.policy_checks_passed is True


def test_build_promotion_evidence_fails_when_any_run_below_threshold():
    target_ref = _target_ref()
    run = EvalRun(target_ref=target_ref, status="completed", pass_rate=0.5)

    evidence = build_promotion_evidence(
        target_ref=target_ref, eval_runs=[run], policy_version="1", pass_rate_threshold=0.8
    )

    assert evidence.policy_checks_passed is False


def test_build_promotion_evidence_fails_when_run_not_completed():
    target_ref = _target_ref()
    run = EvalRun(target_ref=target_ref, status="running", pass_rate=None)

    evidence = build_promotion_evidence(
        target_ref=target_ref, eval_runs=[run], policy_version="1", pass_rate_threshold=0.8
    )

    assert evidence.policy_checks_passed is False


def test_build_promotion_evidence_fails_when_no_eval_runs_at_all():
    target_ref = _target_ref()

    evidence = build_promotion_evidence(
        target_ref=target_ref, eval_runs=[], policy_version="1", pass_rate_threshold=0.8
    )

    assert evidence.policy_checks_passed is False
    assert evidence.required_eval_run_ids == []
