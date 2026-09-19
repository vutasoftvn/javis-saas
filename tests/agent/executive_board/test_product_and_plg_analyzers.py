"""Unit tests for Product, SaaS Metrics & PLG Quantitative Analyzers."""

from __future__ import annotations

import pytest
from agent.executive_board.analyzers import (
    analyze_feature_investment_roi,
    calculate_compounded_churn,
    calculate_viral_k_factor,
    diagnose_saas_health_scorecard,
    score_growth_experiment_ice,
)


def test_calculate_compounded_churn():
    # 3% monthly churn = ~30.62% annual churn (compounded), NOT 36%
    res = calculate_compounded_churn(3.0)
    assert res["monthly_churn_pct"] == 3.0
    assert res["annual_churn_pct"] == 30.62
    assert res["simple_multiplication_pct"] == 36.0
    assert res["compounding_difference_pp"] == 5.38
    assert res["status"] == "crisis"  # > 30%

    # 0.5% monthly churn = ~5.84% annual churn -> "great"
    res_low = calculate_compounded_churn(0.5)
    assert res_low["annual_churn_pct"] == 5.84
    assert res_low["status"] == "great"

    # 1.5% monthly churn = ~16.59% annual churn -> "ok"
    res_mid = calculate_compounded_churn(1.5)
    assert res_mid["annual_churn_pct"] == 16.59
    assert res_mid["status"] == "ok"

    with pytest.raises(ValueError, match="monthly_churn_pct"):
        calculate_compounded_churn(-1.0)
    with pytest.raises(ValueError, match="monthly_churn_pct"):
        calculate_compounded_churn(105.0)


def test_diagnose_saas_health_scorecard_healthy():
    metrics = {
        "revenue_growth_yoy_pct": 80.0,
        "nrr_pct": 125.0,
        "monthly_churn_pct": 1.0,
        "quick_ratio": 4.5,
        "ltv_to_cac": 4.0,
        "cac_payback_months": 8.0,
        "gross_margin_pct": 80.0,
        "runway_months": 24.0,
        "rule_of_40": 48.0,
        "magic_number": 1.2,
    }
    scorecard = diagnose_saas_health_scorecard(metrics, stage="early")
    assert scorecard["overall_status"] == "healthy"
    assert scorecard["red_flag_count"] == 0


def test_diagnose_saas_health_scorecard_critical():
    metrics = {
        "nrr_pct": 85.0,  # Critical flag: < 90%
        "ltv_to_cac": 1.2,  # Critical flag: < 1.5
        "runway_months": 4.0,  # Critical flag: < 6
        "rule_of_40": 15.0,  # High flag: < 25
        "gross_margin_pct": 55.0,  # High flag: < 60%
    }
    scorecard = diagnose_saas_health_scorecard(metrics, stage="early")
    assert scorecard["overall_status"] == "critical"
    assert scorecard["red_flag_count"] == 5
    critical_metrics = [f["metric"] for f in scorecard["red_flags"] if f["severity"] == "critical"]
    assert "nrr_pct" in critical_metrics
    assert "ltv_to_cac" in critical_metrics
    assert "runway_months" in critical_metrics


def test_score_growth_experiment_ice():
    # Impact=8, Confidence=7, Ease=9 -> (8 + 7 + 9) / 3 = 8.0
    score = score_growth_experiment_ice(8.0, 7.0, 9.0)
    assert score == 8.0

    score_decimal = score_growth_experiment_ice(7.0, 8.0, 7.0)
    assert score_decimal == 7.33

    with pytest.raises(ValueError, match="impact"):
        score_growth_experiment_ice(0.5, 7.0, 8.0)
    with pytest.raises(ValueError, match="confidence"):
        score_growth_experiment_ice(8.0, 11.0, 8.0)
    with pytest.raises(ValueError, match="ease"):
        score_growth_experiment_ice(8.0, 7.0, -1.0)


def test_calculate_viral_k_factor():
    # 5 invites sent per user, 10% conversion -> K = 0.5 (viral_assisted)
    res = calculate_viral_k_factor(5.0, 10.0)
    assert res["k_factor"] == 0.5
    assert res["tier"] == "viral_assisted"
    assert res["estimated_cac_reduction_pct"] == 50.0

    # 10 invites sent, 15% conversion -> K = 1.5 (exponential)
    res_exp = calculate_viral_k_factor(10.0, 15.0)
    assert res_exp["k_factor"] == 1.5
    assert res_exp["tier"] == "exponential"
    assert res_exp["estimated_cac_reduction_pct"] == 100.0

    # 1 invite sent, 5% conversion -> K = 0.05 (non_viral)
    res_low = calculate_viral_k_factor(1.0, 5.0)
    assert res_low["k_factor"] == 0.05
    assert res_low["tier"] == "non_viral"
    assert res_low["estimated_cac_reduction_pct"] == 5.0

    with pytest.raises(ValueError, match="không hợp lệ"):
        calculate_viral_k_factor(-1.0, 10.0)


def test_analyze_feature_investment_roi():
    # Direct monetization: dev cost $20k, expected $100k, COGS $10k -> Net $90k -> ROI 4.5, Margin 90% -> build_now
    res = analyze_feature_investment_roi(
        dev_cost=20_000.0,
        expected_annual_value=100_000.0,
        cogs_annual=10_000.0,
        feature_type="direct_monetization",
    )
    assert res["net_annual_value"] == 90_000.0
    assert res["roi"] == 4.5
    assert res["contribution_margin_pct"] == 90.0
    assert res["decision"] == "build_now"

    # Retention feature: ROI 6.0 -> build_now
    res_ret = analyze_feature_investment_roi(
        dev_cost=10_000.0,
        expected_annual_value=60_000.0,
        feature_type="retention",
    )
    assert res_ret["roi"] == 6.0
    assert res_ret["decision"] == "build_now"

    # Strategic feature with low ROI (1.2) -> build_with_governance
    res_strat = analyze_feature_investment_roi(
        dev_cost=50_000.0,
        expected_annual_value=60_000.0,
        feature_type="strategic",
    )
    assert res_strat["decision"] == "build_with_governance"

    # Low ROI non-strategic (< 1.0) -> dont_build
    res_dont = analyze_feature_investment_roi(
        dev_cost=50_000.0,
        expected_annual_value=30_000.0,
        feature_type="direct_monetization",
    )
    assert res_dont["decision"] == "dont_build"

    with pytest.raises(ValueError, match="dev_cost"):
        analyze_feature_investment_roi(0, 1000.0)
