"""Unit tests for Expanded Quantitative Analyzers (13 remaining C-Level roles, 12WY)."""

from __future__ import annotations

import pytest

from agent.executive_board.analyzers import (
    audit_ip_assignment_coverage,
    calculate_12wy_execution_score,
    calculate_attack_surface_expansion,
    calculate_blended_cac,
    calculate_cac_payback_weeks,
    calculate_contract_legal_risk_score,
    calculate_customer_health_distribution,
    calculate_data_pipeline_downtime_impact,
    calculate_data_quality_score,
    calculate_deliberation_consensus_index,
    calculate_dora_score,
    calculate_feature_adoption_rate,
    calculate_hiring_ramp_cost,
    calculate_llm_cost_per_work_unit,
    calculate_nrr_grr_weekly,
    calculate_pipeline_velocity_weekly,
    calculate_sales_capacity_model,
    calculate_security_posture_score,
    calculate_talent_retention_risk,
    calculate_team_sprint_velocity_stability,
    calculate_unit_economics_health,
    evaluate_agent_autonomy_risk_score,
    identify_critical_path_bottlenecks,
    model_cash_runway_stress_test,
    model_channel_efficiency_matrix,
    score_meeting_actionability,
    score_product_bets_rice,
)


# --- 1. CFO Analyzers ---
def test_cfo_cac_payback_weeks():
    # CAC = $1200, ARPU/tuần = $100, Gross Margin = 60% -> weekly margin = $60 -> 20 weeks
    payback = calculate_cac_payback_weeks(1200.0, 100.0, 60.0)
    assert payback == 20.0
    assert calculate_cac_payback_weeks(0, 100.0, 60.0) == 0.0


def test_cfo_model_cash_runway_stress_test():
    res = model_cash_runway_stress_test(
        cash=100_000.0,
        weekly_revenue=10_000.0,
        weekly_cogs=3_000.0,
        weekly_opex=12_000.0,
        shock_factor=0.3,
    )
    # Base burn = 15000 - 10000 = 5000 -> 20 weeks
    # Stressed rev = 7000 -> Stressed burn = 8000 -> 12.5 weeks
    assert res["base_runway_weeks"] == 20.0
    assert res["stressed_runway_weeks"] == 12.5
    assert res["status"] == "critical"  # < 16 weeks


def test_cfo_unit_economics_health():
    res_healthy = calculate_unit_economics_health(cac=500.0, ltv=2000.0, weekly_churn_rate=0.005)
    assert res_healthy["status"] == "healthy"
    assert res_healthy["ltv_to_cac_ratio"] == 4.0

    res_warning = calculate_unit_economics_health(cac=1000.0, ltv=2200.0, weekly_churn_rate=0.02)
    assert res_warning["status"] == "warning"


# --- 2. CPO Analyzers ---
def test_cpo_score_product_bets_rice():
    # Reach = 500, Impact = 2.0, Confidence = 0.8, Effort = 4 weeks -> (500*2*0.8)/4 = 200.0
    score = score_product_bets_rice(500, 2.0, 0.8, 4.0)
    assert score == 200.0

    with pytest.raises(ValueError):
        score_product_bets_rice(100, 1.0, 1.0, 0.0)


def test_cpo_calculate_feature_adoption_rate():
    strong = calculate_feature_adoption_rate(45, 100, weeks_since_launch=3)
    assert strong["status"] == "strong"
    assert strong["kill_candidate"] is False

    kill = calculate_feature_adoption_rate(10, 100, weeks_since_launch=8)
    assert kill["status"] == "at_risk"
    assert kill["kill_candidate"] is True


# --- 3. CMO Analyzers ---
def test_cmo_calculate_blended_cac():
    cac = calculate_blended_cac(5000.0, 3000.0, 40)
    assert cac == 200.0
    assert calculate_blended_cac(5000.0, 3000.0, 0) == 0.0


def test_cmo_model_channel_efficiency_matrix():
    channels = [
        {"name": "Google Ads", "spend_weekly": 2000.0, "customers_acquired_weekly": 10, "target_cac": 150.0},
        {"name": "SEO", "spend_weekly": 500.0, "customers_acquired_weekly": 10, "target_cac": 100.0},
    ]
    res = model_channel_efficiency_matrix(channels)
    assert res[0]["channel_name"] == "SEO"
    assert res[0]["efficiency"] == "high"
    assert res[1]["channel_name"] == "Google Ads"
    assert res[1]["efficiency"] == "low"


# --- 4. CRO Analyzers ---
def test_cro_pipeline_velocity_weekly():
    # 20 deals, 25% win rate, ACV $10,000, cycle = 5 weeks -> (20 * 0.25 * 10000) / 5 = $10,000 / week
    vel = calculate_pipeline_velocity_weekly(20, 0.25, 10_000.0, 5.0)
    assert vel == 10_000.0


def test_cro_sales_capacity_model():
    cap = calculate_sales_capacity_model(4, 5000.0, ramp_factor=0.8)
    assert cap["max_weekly_capacity"] == 20_000.0
    assert cap["realistic_weekly_capacity"] == 16_000.0


# --- 5. CCO Analyzers ---
def test_cco_nrr_grr_weekly():
    res = calculate_nrr_grr_weekly(
        starting_arr=100_000.0,
        expansion=15_000.0,
        contraction=2_000.0,
        churn=3_000.0,
    )
    # NRR = (100k + 15k - 2k - 3k) / 100k = 110.0%
    # GRR = (100k - 2k - 3k) / 100k = 95.0%
    assert res["nrr_pct"] == 110.0
    assert res["grr_pct"] == 95.0


def test_cco_customer_health_distribution():
    accounts = [
        {"id": "1", "health_score": 90},
        {"id": "2", "health_score": 75},
        {"id": "3", "health_score": 40},
    ]
    dist = calculate_customer_health_distribution(accounts)
    assert dist["green_pct"] == 33.3
    assert dist["high_risk_count"] == 1


# --- 6. COO Analyzers ---
def test_coo_12wy_execution_score():
    score = calculate_12wy_execution_score(9, 10)
    assert score == 90.0
    assert calculate_12wy_execution_score(0, 0) == 100.0


def test_coo_identify_critical_path_bottlenecks():
    tasks = [
        {"id": "t1", "name": "API Refactor", "is_blocker": True, "days_delayed": 5, "stream": "backend"},
        {"id": "t2", "name": "Copywrite", "is_blocker": False, "days_delayed": 1, "is_critical_path": False},
    ]
    bottlenecks = identify_critical_path_bottlenecks(tasks)
    assert len(bottlenecks) == 1
    assert bottlenecks[0]["task_id"] == "t1"


# --- 7. VPE Analyzers ---
def test_vpe_dora_score():
    elite = calculate_dora_score(deployment_freq_weekly=10.0, lead_time_hours=12.0, change_failure_pct=2.0, mttr_hours=0.5)
    assert elite["tier"] == "elite"

    high = calculate_dora_score(deployment_freq_weekly=2.0, lead_time_hours=48.0, change_failure_pct=10.0, mttr_hours=5.0)
    assert high["tier"] == "high"


def test_vpe_team_sprint_velocity_stability():
    res = calculate_team_sprint_velocity_stability([40.0, 42.0, 39.0, 41.0])
    assert res["avg_velocity"] == 40.5
    assert res["stability_cv_pct"] < 5.0


# --- 8. CHRO Analyzers ---
def test_chro_hiring_ramp_cost():
    # Salary $104k -> $2000/tuần. 12 tuần ramp -> 12 * 2000 * 0.5 = $12k. Recruiter = $5k -> Total $17k
    cost = calculate_hiring_ramp_cost(role_salary=104_000.0, recruiter_cost=5_000.0, ramp_weeks=12)
    assert cost == 17_000.0


def test_chro_talent_retention_risk():
    team = [
        {"name": "Alice", "role": "Staff Eng", "flight_risk_score": 0.8, "is_single_point_of_failure": True},
        {"name": "Bob", "role": "Dev", "flight_risk_score": 0.2, "is_single_point_of_failure": False},
    ]
    risks = calculate_talent_retention_risk(team)
    assert len(risks) == 1
    assert risks[0]["name"] == "Alice"
    assert risks[0]["risk_level"] == "critical"


# --- 9. CISO Analyzers ---
def test_ciso_security_posture_score():
    clean = calculate_security_posture_score(critical_cves=0, high_cves=0, unpatched_weeks_avg=0, mfa_coverage_pct=100.0)
    assert clean["posture_score"] == 100.0
    assert clean["status"] == "secure"

    vuln = calculate_security_posture_score(critical_cves=2, high_cves=3, unpatched_weeks_avg=2.0, mfa_coverage_pct=80.0)
    # Deduction: 2*25 + 3*10 + 2*5 = 90. MFA penalty = 10. Total 100 -> score = 0
    assert vuln["status"] == "critical_risk"


def test_ciso_attack_surface_expansion():
    # 4 endpoints * 1.5 + 2 integrations * 5.0 = 6.0 + 10.0 = 16.0
    surf = calculate_attack_surface_expansion(4, 2, auth_bypass_risk=False)
    assert surf == 16.0


# --- 10. GC Analyzers ---
def test_gc_contract_legal_risk_score():
    risk_low = calculate_contract_legal_risk_score(indemnity_cap=1_000_000.0, sla_penalty_pct=10.0, ip_reversion_clause=False)
    assert risk_low == 2.0

    risk_high = calculate_contract_legal_risk_score(indemnity_cap=0, sla_penalty_pct=25.0, ip_reversion_clause=True)
    assert risk_high >= 8.0


def test_gc_audit_ip_assignment_coverage():
    res = audit_ip_assignment_coverage(10, 10)
    assert res["status"] == "compliant"

    res_missing = audit_ip_assignment_coverage(10, 8)
    assert res_missing["status"] == "non_compliant_blocking"
    assert res_missing["unassigned_count"] == 2


# --- 11. CDO Analyzers ---
def test_cdo_data_quality_score():
    # Completeness 90% (36), Accuracy 95% (38), Freshness 5h -> Freshness score = 90 (18) -> Total = 92.0
    score = calculate_data_quality_score(90.0, 95.0, 5.0)
    assert score == 92.0


def test_cdo_data_pipeline_downtime_impact():
    res = calculate_data_pipeline_downtime_impact(weekly_downtime_hours=6.0, impacted_users=500)
    assert res["severity"] == "high"


# --- 12. CAIO Analyzers ---
def test_caio_llm_cost_per_work_unit():
    # 500k input + 500k output = 1M tokens * $2.5/M = $2.50
    cost = calculate_llm_cost_per_work_unit(500_000, 500_000, 2.50)
    assert cost == 2.50


def test_caio_evaluate_agent_autonomy_risk_score():
    low = evaluate_agent_autonomy_risk_score("L1_PROPOSE", tool_side_effects_count=0)
    assert low["governance_guardrail_needed"] is False

    high = evaluate_agent_autonomy_risk_score("L3_EXECUTE", tool_side_effects_count=5)
    assert high["governance_guardrail_needed"] is True


# --- 13. Chief of Staff Analyzers ---
def test_cos_consensus_index():
    # 3 votes for A, 1 vote for B -> 3/4 = 0.75
    votes = {"ceo": "Option A", "cto": "Option A", "cpo": "Option A", "cfo": "Option B"}
    assert calculate_deliberation_consensus_index(votes) == 0.75


def test_cos_meeting_actionability():
    # Base 6 + 3 (binding) + 1 (dissent) = 10.0
    score = score_meeting_actionability(dissent_count=1, binding_criteria_present=True)
    assert score == 10.0
