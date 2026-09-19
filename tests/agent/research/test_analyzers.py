"""Comprehensive Unit Tests for Research & Research-Ops Quantitative Analyzers."""

import pytest

from agent.research.analyzers.disconfirming_evidence_checker import (
    DisconfirmingEvidenceChecker,
)
from agent.research.analyzers.market_sizing_triangulator import (
    MarketSizingTriangulator,
)
from agent.research.analyzers.rd_capex_opex_router import (
    RDCapexOpexRouter,
)
from agent.research.analyzers.research_saturation_modeler import (
    ResearchSaturationModeler,
)
from agent.research.analyzers.source_tier_classifier import (
    SourceTierClassifier,
)
from agent.research.analyzers.survey_sample_planner import (
    SurveySamplePlanner,
)


# ============================================================================
# 1. MarketSizingTriangulator Tests
# ============================================================================

def test_market_sizing_top_down():
    triangulator = MarketSizingTriangulator(profile="b2b-saas")
    res = triangulator.calculate_top_down(
        total_market_value=1_000_000_000,
        serviceable_fraction=0.40,
        reachable_share=0.05,
    )
    assert res.tam == 1_000_000_000
    assert res.sam == 400_000_000
    assert res.som == 20_000_000


def test_market_sizing_bottoms_up():
    triangulator = MarketSizingTriangulator(profile="b2b-saas")
    res = triangulator.calculate_bottoms_up(
        total_potential_customers=50_000,
        annual_price=20_000,
        serviceable_fraction=0.40,
        realistic_adoption=0.02,
    )
    assert res.tam == 1_000_000_000
    assert res.sam == 400_000_000
    assert res.som == 8_000_000
    assert res.implied_customers_at_som == 400


def test_market_sizing_triangulation_passed():
    triangulator = MarketSizingTriangulator(profile="b2b-saas")
    report = triangulator.triangulate(
        market_name="HR Cloud",
        top_down_input={
            "total_market_value": 1_000_000_000,
            "serviceable_fraction": 0.30,
            "reachable_share": 0.05,
        },
        bottoms_up_input={
            "total_potential_customers": 45_000,
            "annual_price": 20_000,  # TAM = 900,000,000 (10% delta)
            "serviceable_fraction": 0.30,
            "realistic_adoption": 0.05,
        },
    )
    assert report.triangulation_passed is True
    assert report.tam_divergence == 0.10
    assert any("Triangulation OK" in f for f in report.flags)


def test_market_sizing_triangulation_failed_flag():
    triangulator = MarketSizingTriangulator(profile="b2b-saas")  # tolerance 30%
    report = triangulator.triangulate(
        market_name="AI Analytics",
        top_down_input={
            "total_market_value": 2_000_000_000,
            "serviceable_fraction": 0.20,
            "reachable_share": 0.05,
        },
        bottoms_up_input={
            "total_potential_customers": 40_000,
            "annual_price": 20_000,  # TAM = 800,000,000 (60% delta)
            "serviceable_fraction": 0.20,
            "realistic_adoption": 0.05,
        },
    )
    assert report.triangulation_passed is False
    assert report.tam_divergence == 0.60
    assert any("TRIANGULATION FAILED" in f for f in report.flags)


def test_market_sizing_invalid_profile():
    with pytest.raises(ValueError):
        MarketSizingTriangulator(profile="unknown-profile")


# ============================================================================
# 2. SurveySamplePlanner Tests
# ============================================================================

def test_survey_sample_planner_infinite_population():
    planner = SurveySamplePlanner()
    plan = planner.plan_sample(
        margin_of_error=0.05,
        confidence_level=0.95,
        response_rate=0.20,
    )
    # Cochran 95% CI (Z=1.96), p=0.5, e=0.05 -> ~385 completes
    assert plan.recommended_sample_size == 385
    assert plan.is_finite is False
    assert plan.invites_needed == 1925  # 385 / 0.20 = 1925


def test_survey_sample_planner_finite_population():
    planner = SurveySamplePlanner()
    plan = planner.plan_sample(
        margin_of_error=0.05,
        confidence_level=0.95,
        population_size=1000,
        response_rate=0.25,
    )
    # Finite correction on N=1000 reduces sample size from 385 to ~278
    assert plan.is_finite is True
    assert 270 <= plan.recommended_sample_size <= 285
    assert plan.invites_needed == 1112  # ceil(278 / 0.25)


def test_survey_sample_planner_margin_of_error_calc():
    planner = SurveySamplePlanner()
    moe = planner.calculate_margin_of_error(sample_size=385, confidence_level=0.95)
    assert 0.049 <= moe <= 0.051


def test_survey_sample_planner_invalid_inputs():
    planner = SurveySamplePlanner()
    with pytest.raises(ValueError):
        planner.plan_sample(margin_of_error=0.50)  # excessive error
    with pytest.raises(ValueError):
        planner.plan_sample(response_rate=0.0)


# ============================================================================
# 3. DisconfirmingEvidenceChecker Tests
# ============================================================================

def test_disconfirming_evidence_pass():
    checker = DisconfirmingEvidenceChecker()
    report = checker.evaluate_balance(
        hypothesis="Acme Corp is consolidating all developer tooling into a single suite",
        supporting=7,
        disconfirming=3,  # 3/10 = 30% -> PASS
    )
    assert report.verdict == "PASS"
    assert report.ratio == 0.30
    assert report.remediation_needed is False


def test_disconfirming_evidence_warn():
    checker = DisconfirmingEvidenceChecker()
    report = checker.evaluate_balance(
        hypothesis="Product X is winning all enterprise deals",
        supporting=8,
        disconfirming=2,  # 2/10 = 20% -> WARN
    )
    assert report.verdict == "WARN"
    assert report.remediation_needed is True
    assert report.disconfirming_needed_to_reach_floor == 1


def test_disconfirming_evidence_fail_high_bias():
    checker = DisconfirmingEvidenceChecker()
    report = checker.evaluate_balance(
        hypothesis="Startup Y is expanding rapidly without competition",
        supporting=9,
        disconfirming=1,  # 1/10 = 10% (< 20%) -> FAIL
    )
    assert report.verdict == "FAIL"
    assert report.remediation_needed is True
    assert "DỪNG XUẤT BÁO CÁO" in report.message


def test_antonym_pivot_suggestions():
    checker = DisconfirmingEvidenceChecker()
    suggestions = checker.suggest_disconfirming_queries("Company Z is growing revenue and hiring aggressively")
    assert any("shrinking" in s or "declining" in s for s in suggestions)
    assert any("laying off" in s or "turnover" in s for s in suggestions)


# ============================================================================
# 4. SourceTierClassifier Tests
# ============================================================================

def test_source_tier_primary():
    classifier = SourceTierClassifier()
    res1 = classifier.classify_url("https://www.sec.gov/edgar/searchedgar/companysearch")
    assert res1.tier == "PRIMARY"
    assert res1.weight == 1.0

    res2 = classifier.classify_url("https://data.chinhphu.vn/thong-ke")
    assert res2.tier == "PRIMARY"

    res3 = classifier.classify_url("https://patents.google.com/patent/US1012345B2")
    assert res3.tier == "PRIMARY"


def test_source_tier_secondary():
    classifier = SourceTierClassifier()
    res1 = classifier.classify_url("https://techcrunch.com/2026/08/saas-trends")
    assert res1.tier == "SECONDARY"
    assert res1.weight == 0.7

    res2 = classifier.classify_url("https://vnexpress.net/kinh-doanh-cong-nghe")
    assert res2.tier == "SECONDARY"


def test_source_tier_tertiary():
    classifier = SourceTierClassifier()
    res1 = classifier.classify_url("https://www.reddit.com/r/startups/comments/123/thoughts")
    assert res1.tier == "TERTIARY"
    assert res1.weight == 0.4

    res2 = classifier.classify_url("https://voz.vn/t/cong-nghe-moi.1234/")
    assert res2.tier == "TERTIARY"


def test_source_inventory_evaluation():
    classifier = SourceTierClassifier()
    urls = [
        "https://www.sec.gov/edgar/annual-report",
        "https://reuters.com/business/tech-merger",
        "https://bloomberg.com/news/articles/2026-05",
        "https://reddit.com/r/technology",
    ]
    report = classifier.evaluate_inventory(urls)
    assert report.total_sources == 4
    assert report.primary_count == 1
    assert report.secondary_count == 2
    assert report.tertiary_count == 1
    assert report.average_credibility_score == round((1.0 + 0.7 + 0.7 + 0.4) / 4, 3)
    assert report.quality_verdict in ("HIGH_INTEGRITY", "ACCEPTABLE")


# ============================================================================
# 5. ResearchSaturationModeler Tests
# ============================================================================

def test_research_saturation_usability_nielsen():
    modeler = ResearchSaturationModeler()
    # At 84% target coverage, 5 users is sufficient: 1 - (1-0.31)^5 = 84.4%
    plan_5 = modeler.plan_usability_study(segments=2, detection_rate=0.31, target_coverage=0.84)
    assert plan_5.n_per_segment == 5
    assert plan_5.total_participants == 10
    assert plan_5.expected_coverage >= 0.84

    # At 85% target coverage, mathematically ceil(log(0.15)/log(0.69)) = 6 users
    plan_6 = modeler.plan_usability_study(segments=1, detection_rate=0.31, target_coverage=0.85)
    assert plan_6.n_per_segment == 6
    assert plan_6.expected_coverage >= 0.89


def test_research_saturation_thematic_guest():
    modeler = ResearchSaturationModeler()
    plan_std = modeler.plan_thematic_study(segments=1, stakes_high_or_heterogeneous=False)
    assert plan_std.n_per_segment == 12

    plan_high = modeler.plan_thematic_study(segments=1, stakes_high_or_heterogeneous=True)
    assert plan_high.n_per_segment == 15


def test_insight_linter_flags_single_participant():
    modeler = ResearchSaturationModeler()
    claims = [
        {"id": 1, "statement": "Người dùng cần tính năng export Excel vì khó khăn khi tổng hợp.", "participant_count": 1, "label": "INSIGHT"},
        {"id": 2, "statement": "Quy trình thanh toán hiện tại bị nghẽn ở bước OTP.", "participant_count": 5, "label": "INSIGHT"},
    ]
    report = modeler.lint_insight_claims(claims)
    assert report.is_compliant is False
    assert report.anecdote_count == 1
    assert report.insight_count == 1
    assert report.violations[0].violation_rule == "SINGLE_PARTICIPANT_ASSERTION"


# ============================================================================
# 6. RDCapexOpexRouter Tests
# ============================================================================

def test_rd_capex_opex_research_phase():
    router = RDCapexOpexRouter(standard="ifrs")
    item = {
        "id": "R1",
        "name": "Khảo sát thuật toán AI mới",
        "phase": "research",
        "amount": 10000,
        "criteria": {},
    }
    res = router.evaluate_item(item)
    assert res.verdict == "EXPENSE"
    assert "Giai đoạn nghiên cứu" in res.rationale
    assert "R&D Finance Controller" in res.named_owner


def test_rd_capex_opex_development_phase_all_criteria_met():
    router = RDCapexOpexRouter(standard="ifrs")
    item = {
        "id": "D1",
        "name": "Xây dựng core feature SaaS",
        "phase": "development",
        "amount": 50000,
        "criteria": {
            "technical_feasibility": True,
            "intention_to_complete": True,
            "ability_to_use_or_sell": True,
            "probable_future_benefit": True,
            "adequate_resources": True,
            "reliable_measurement": True,
        },
    }
    res = router.evaluate_item(item)
    assert res.verdict == "CAPITALIZE-CANDIDATE"
    assert "đạt đủ 6/6 tiêu chí" in res.rationale
    assert "External Auditor" in res.named_owner


def test_rd_capex_opex_development_missing_criteria():
    router = RDCapexOpexRouter(standard="ifrs")
    item = {
        "id": "D2",
        "name": "Xây dựng microservice mới",
        "phase": "development",
        "amount": 25000,
        "criteria": {
            "technical_feasibility": True,
            "intention_to_complete": True,
            "ability_to_use_or_sell": True,
            "probable_future_benefit": True,
            "adequate_resources": False,  # missing
            "reliable_measurement": True,
        },
    }
    res = router.evaluate_item(item)
    assert res.verdict == "FINANCE-OWNER-REVIEW"
    assert "adequate_resources" in res.criteria_missing


def test_rd_capex_opex_budget_summary():
    router = RDCapexOpexRouter(standard="ifrs")
    items = [
        {"id": "1", "name": "Ideation", "phase": "research", "amount": 10000},
        {
            "id": "2",
            "name": "Build",
            "phase": "development",
            "amount": 30000,
            "criteria": {k: True for k in [
                "technical_feasibility", "intention_to_complete",
                "ability_to_use_or_sell", "probable_future_benefit",
                "adequate_resources", "reliable_measurement"
            ]},
        },
    ]
    report = router.route_budget(items)
    assert report.total_spend == 40000
    assert report.total_expense_candidate == 10000
    assert report.total_capitalize_candidate == 30000
