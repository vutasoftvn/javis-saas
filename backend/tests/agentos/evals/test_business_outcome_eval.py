# backend/tests/agentos/evals/test_business_outcome_eval.py
from agentos.evals.business_outcome_eval import evaluate_business_outcome


def test_evaluate_business_outcome_full_achievement():
    result = evaluate_business_outcome("kr_hit_10k_mrr", target=10000, actual=10000)
    assert result.achievement_ratio == 1.0
    assert result.achieved is True


def test_evaluate_business_outcome_partial_achievement():
    result = evaluate_business_outcome("kr_hit_10k_mrr", target=10000, actual=2500)
    assert result.achievement_ratio == 0.25
    assert result.achieved is False


def test_evaluate_business_outcome_clamps_at_one_when_actual_exceeds_target():
    result = evaluate_business_outcome("kr_hit_10k_mrr", target=10000, actual=15000)
    assert result.achievement_ratio == 1.0
    assert result.achieved is True


def test_evaluate_business_outcome_handles_zero_target():
    result = evaluate_business_outcome("ctr", target=0, actual=5)
    assert result.achievement_ratio == 0.0
    assert result.achieved is False
