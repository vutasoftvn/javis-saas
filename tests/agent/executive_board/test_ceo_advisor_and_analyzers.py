from __future__ import annotations

import pytest

from agent.executive_board.analyzers import (
    EvaluationCriterion,
    FinancialScenarioAnalyzer,
    StrategicOption,
    StrategyAnalyzer,
)
from agent.executive_board.skill_pins import parse_skill_pin_ref
from apps.cosa.agents.executive_advisor_roles_generated import (
    EXECUTIVE_ROLE_CATALOG,
    EXECUTIVE_ROLE_KEYS,
)


def test_ceo_role_registered_in_catalog():
    assert "ceo" in EXECUTIVE_ROLE_KEYS
    ceo_def = EXECUTIVE_ROLE_CATALOG["ceo"]
    assert ceo_def.key == "ceo"
    assert ceo_def.required_profile_key == "operations"
    assert ceo_def.required_agent_spec == "cosa.executive.ceo"
    assert "skillpack:executive/ceo-advisor@1.0.0" in ceo_def.required_skill_pins
    assert ceo_def.advisory_only is True
    assert ceo_def.runtime_readiness == "READY"


def test_parse_ceo_skill_pin():
    skill_id, version = parse_skill_pin_ref("skillpack:executive/ceo-advisor@1.0.0")
    assert skill_id == "executive.ceo-advisor"
    assert version == "1.0.0"


def test_strategy_analyzer_scoring():
    criteria = [
        EvaluationCriterion(id="impact", label="Strategic Impact", weight=0.5),
        EvaluationCriterion(id="cost", label="Capital Efficiency", weight=0.3),
        EvaluationCriterion(id="speed", label="Speed to Market", weight=0.2),
    ]

    options = [
        StrategicOption(
            id="opt-a",
            title="Option A: Focus on B2B SaaS",
            description="Pivot core product to mid-market B2B",
            scores={"impact": 9.0, "cost": 7.0, "speed": 6.0},
            reversibility="medium",
            second_order_effects=("Increases ACV", "Requires sales hire"),
        ),
        StrategicOption(
            id="opt-b",
            title="Option B: Expand Consumer PLG",
            description="Double down on viral consumer acquisition",
            scores={"impact": 6.0, "cost": 9.0, "speed": 8.0},
            reversibility="high",
            second_order_effects=("Lower margin per user", "Requires ad spend"),
        ),
    ]

    results = StrategyAnalyzer.score_options(options, criteria)

    assert len(results) == 2
    # Option A: 9.0*0.5 + 7.0*0.3 + 6.0*0.2 = 4.5 + 2.1 + 1.2 = 7.8
    # Option B: 6.0*0.5 + 9.0*0.3 + 8.0*0.2 = 3.0 + 2.7 + 1.6 = 7.3
    assert results[0]["option_id"] == "opt-a"
    assert results[0]["weighted_score"] == 7.8
    assert results[0]["rank"] == 1
    assert results[0]["reversibility"] == "medium"

    assert results[1]["option_id"] == "opt-b"
    assert results[1]["weighted_score"] == 7.3
    assert results[1]["rank"] == 2


def test_strategy_analyzer_invalid_weights():
    criteria = [EvaluationCriterion(id="impact", label="Impact", weight=0.0)]
    options = [
        StrategicOption(
            id="opt-1",
            title="Opt 1",
            description="",
            scores={},
            reversibility="high",
        )
    ]
    with pytest.raises(ValueError, match="Tổng trọng số"):
        StrategyAnalyzer.score_options(options, criteria)


def test_financial_scenario_analyzer_modeling():
    # 500k cash, 50k burn, 10k revenue, 5% growth
    model = FinancialScenarioAnalyzer.model_scenarios(
        current_cash=500_000,
        monthly_burn=50_000,
        monthly_revenue=10_000,
        growth_rate_pct=5.0,
        forecast_months=12,
    )

    assert model["current_cash"] == 500_000
    assert "scenarios" in model
    base = model["scenarios"]["base"]
    bull = model["scenarios"]["bull"]
    bear = model["scenarios"]["bear"]

    assert base["runway_months"] > 0
    assert bull["ending_cash"] > base["ending_cash"]
    assert bear["ending_cash"] < base["ending_cash"]
    assert base["fundraising_trigger_month"] >= 1


def test_financial_scenario_analyzer_invalid_burn():
    with pytest.raises(ValueError, match="không được là số âm"):
        FinancialScenarioAnalyzer.model_scenarios(
            current_cash=100_000,
            monthly_burn=-10_000,
        )


def test_calculate_weeks_of_runway():
    # 240,000 cash, 12,000 weekly burn, 2,000 weekly rev -> net burn 10,000/week -> 24.0 weeks
    runway = FinancialScenarioAnalyzer.calculate_weeks_of_runway(
        current_cash=240_000,
        weekly_burn=12_000,
        weekly_revenue=2_000,
    )
    assert runway == 24.0

    # Zero burn -> infinity
    inf_runway = FinancialScenarioAnalyzer.calculate_weeks_of_runway(
        current_cash=100_000,
        weekly_burn=5_000,
        weekly_revenue=5_000,
    )
    assert inf_runway == float("inf")


def test_financial_scenario_analyzer_weekly_12wy():
    # 480k cash, 10k weekly burn, 2k weekly revenue -> forecast 48 weeks (4 cycles 12WY)
    model = FinancialScenarioAnalyzer.model_weekly_scenarios(
        current_cash=480_000,
        weekly_burn=10_000,
        weekly_revenue=2_000,
        weekly_growth_pct=1.0,
        forecast_weeks=48,
    )

    assert model["current_cash"] == 480_000
    assert model["weekly_burn"] == 10_000
    assert "scenarios" in model
    base = model["scenarios"]["base"]
    bull = model["scenarios"]["bull"]
    bear = model["scenarios"]["bear"]

    assert base["runway_weeks"] > 0
    assert base["cycle_12w_burn"] == 8_000 * 12  # (10k - 2k) * 12 = 96,000
    assert bull["ending_cash"] > base["ending_cash"]
    assert bear["ending_cash"] < base["ending_cash"]
    assert base["fundraising_trigger_week"] >= 1

