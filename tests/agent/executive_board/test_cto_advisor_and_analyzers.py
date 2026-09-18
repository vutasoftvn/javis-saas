from __future__ import annotations

import pytest

from agent.executive_board.analyzers import (
    BuildVsBuyAnalyzer,
    BuildVsBuyOption,
    EvaluationCriterion,
    TechDebtAnalyzer,
    TechDebtItem,
)
from agent.executive_board.skill_pins import parse_skill_pin_ref
from agent.governance.contracts import AutonomyLevel
from apps.cosa.agents.executive_advisor_roles_generated import (
    EXECUTIVE_ROLE_CATALOG,
    EXECUTIVE_ROLE_KEYS,
)
from apps.cosa.agents.specs import (
    COSA_EXECUTIVE_CTO_AGENT_SPEC,
    EXECUTIVE_AGENT_SPECS,
)


def test_cto_role_registered_in_catalog():
    assert "cto" in EXECUTIVE_ROLE_KEYS
    cto_def = EXECUTIVE_ROLE_CATALOG["cto"]
    assert cto_def.key == "cto"
    assert cto_def.required_profile_key == "coding"
    assert cto_def.required_agent_spec == "cosa.executive.cto"
    assert "skillpack:executive/cto-advisor@1.0.0" in cto_def.required_skill_pins
    assert cto_def.advisory_only is True
    assert cto_def.runtime_readiness == "READY"


def test_parse_cto_skill_pin():
    skill_id, version = parse_skill_pin_ref("skillpack:executive/cto-advisor@1.0.0")
    assert skill_id == "executive.cto-advisor"
    assert version == "1.0.0"


def test_cto_agent_spec_registration():
    assert "cosa.executive.cto" in EXECUTIVE_AGENT_SPECS
    spec = EXECUTIVE_AGENT_SPECS["cosa.executive.cto"]
    assert spec == COSA_EXECUTIVE_CTO_AGENT_SPEC
    assert spec.id == "cosa.executive.cto"
    assert spec.autonomy_level == AutonomyLevel.L1_PROPOSE
    assert spec.metadata.get("advisory_only") is True


def test_tech_debt_analyzer_empty():
    res = TechDebtAnalyzer.analyze_inventory([])
    assert res["total_items"] == 0
    assert res["total_cost_days"] == 0.0
    assert res["ranked_items"] == []
    assert res["action_buckets"]["immediate_sprint"] == []


def test_tech_debt_analyzer_prioritization():
    items = [
        TechDebtItem(
            id="td-1",
            title="Legacy Auth API v1",
            category="architecture",
            severity=4,  # P0
            blast_radius=5,
            cost_to_fix_days=10.0,
        ),
        TechDebtItem(
            id="td-2",
            title="Unindexed DB Queries in Analytics",
            category="performance",
            severity=3,  # P1
            blast_radius=2,
            cost_to_fix_days=2.0,
        ),
        TechDebtItem(
            id="td-3",
            title="Outdated Deploy Script",
            category="infrastructure",
            severity=1,  # P3
            blast_radius=1,
            cost_to_fix_days=5.0,
        ),
    ]

    res = TechDebtAnalyzer.analyze_inventory(items)
    assert res["total_items"] == 3
    assert res["total_cost_days"] == 17.0
    assert res["category_breakdown"]["architecture"] == 10.0
    assert res["category_breakdown"]["performance"] == 2.0
    assert res["category_breakdown"]["infrastructure"] == 5.0

    ranked = res["ranked_items"]
    # td-2: (3 * 2) / 2.0 = 3.0
    # td-1: (4 * 5) / 10.0 = 2.0
    # td-3: (1 * 1) / 5.0 = 0.2
    assert ranked[0]["id"] == "td-2"
    assert ranked[0]["priority_score"] == 3.0
    assert ranked[1]["id"] == "td-1"
    assert ranked[1]["priority_score"] == 2.0
    assert ranked[2]["id"] == "td-3"
    assert ranked[2]["priority_score"] == 0.2

    # Buckets: td-1 (severity 4) -> immediate, td-2 (score 3.0) -> immediate
    # td-3 -> backlog
    immediate_ids = [it["id"] for it in res["action_buckets"]["immediate_sprint"]]
    assert "td-1" in immediate_ids
    assert "td-2" in immediate_ids
    backlog_ids = [it["id"] for it in res["action_buckets"]["tracked_backlog"]]
    assert "td-3" in backlog_ids


def test_tech_debt_analyzer_invalid_cost():
    item = TechDebtItem(
        id="td-bad",
        title="Bad",
        category="security",
        severity=3,
        blast_radius=2,
        cost_to_fix_days=0.0,
    )
    with pytest.raises(ValueError, match="cost_to_fix_days"):
        TechDebtAnalyzer.analyze_inventory([item])


def test_build_vs_buy_analyzer_evaluation():
    criteria = [
        EvaluationCriterion(id="fit", label="Fit for Purpose", weight=0.35),
        EvaluationCriterion(id="tco", label="3-Year TCO", weight=0.30),
        EvaluationCriterion(id="risk", label="Low Migration Risk", weight=0.20),
        EvaluationCriterion(id="speed", label="Speed to Implement", weight=0.15),
    ]

    options = [
        BuildVsBuyOption(
            id="opt-build",
            name="In-House Custom Workflow Engine",
            option_type="build",
            three_year_tco=150_000.0,
            scores={"fit": 9.0, "tco": 4.0, "risk": 8.0, "speed": 4.0},
            migration_risk="low",
            is_core_ip=True,
        ),
        BuildVsBuyOption(
            id="opt-buy",
            name="Commercial SaaS Vendor X",
            option_type="buy",
            three_year_tco=75_000.0,
            scores={"fit": 8.0, "tco": 8.0, "risk": 6.0, "speed": 9.0},
            migration_risk="medium",
            is_core_ip=False,
        ),
    ]

    eval_res = BuildVsBuyAnalyzer.evaluate(options, criteria)
    assert len(eval_res["ranked_options"]) == 2

    # opt-buy: 8.0*0.35 + 8.0*0.30 + 6.0*0.20 + 9.0*0.15 = 2.8 + 2.4 + 1.2 + 1.35 = 7.75
    # opt-build: 9.0*0.35 + 4.0*0.30 + 8.0*0.20 + 4.0*0.15 = 3.15 + 1.2 + 1.6 + 0.6 = 6.55
    top = eval_res["top_pick"]
    assert top["option_id"] == "opt-buy"
    assert top["weighted_score"] == 7.75
    assert "BUY" in eval_res["strategic_rationale"]


def test_build_vs_buy_analyzer_tco_144_weeks():
    criteria = [EvaluationCriterion(id="tco", label="TCO", weight=1.0)]
    options = [
        BuildVsBuyOption(
            id="opt-core",
            name="Core Platform Engine",
            option_type="build",
            three_year_tco=200_000.0,
            tco_144_weeks=190_000.0,
            scores={"tco": 8.0},
            migration_risk="low",
            is_core_ip=True,
        )
    ]
    res = BuildVsBuyAnalyzer.evaluate(options, criteria)
    assert res["top_pick"]["tco_144_weeks"] == 190_000.0
    assert "TỰ XÂY DỰNG" in res["strategic_rationale"]


def test_team_scaling_calculator():
    from agent.executive_board.analyzers import TeamScalingCalculator, TeamScalingPlan

    plan = TeamScalingPlan(
        current_headcount=5,
        target_headcount=13,  # Cần tuyển thêm 8 người qua 4 chu kỳ 12WY (mỗi chu kỳ ~2 người)
        ramp_weeks_per_hire=12,
        weekly_cost_per_head=1000.0,
        hiring_fee_per_head=2000.0,
    )

    res = TeamScalingCalculator.calculate_trajectory(plan, cycles_count=4)
    assert res["current_headcount"] == 5
    assert res["target_headcount"] == 13
    assert res["total_net_hires"] == 8
    assert len(res["cycles"]) == 4
    assert res["cycles"][-1]["end_headcount"] == 13
    assert res["total_projected_cost"] > 0

