from __future__ import annotations

from agent.operations.analyzers import (
    ProcessCycleAnalyzer,
    ProcessStage,
    ProcurementSpendAnalyzer,
    Runbook5W2HValidator,
    RunbookStep,
    SpendItem,
    VendorGovernanceCalculator,
    WorkforceCapacityModeler,
)


def test_process_cycle_analyzer_detects_bottlenecks():
    # Setup process with heavy wait and slow stage
    stages = [
        ProcessStage(id="s1", name="Intake", kind="value_add", duration_minutes=15.0),
        ProcessStage(id="s2", name="Review Queue", kind="wait", duration_minutes=120.0),
        ProcessStage(id="s3", name="Processing", kind="value_add", duration_minutes=60.0),
        ProcessStage(id="s4", name="Rework on errors", kind="rework", duration_minutes=40.0),
    ]
    report = ProcessCycleAnalyzer.analyze(stages, profile="saas")
    assert report.total_cycle_minutes == 235.0
    assert report.value_add_minutes == 75.0
    assert report.wait_minutes == 120.0
    assert report.rework_minutes == 40.0
    assert report.wait_share > 0.40  # Wait share bottleneck

    # Bottlenecks identified
    rule_codes = {b.rule_code for b in report.bottlenecks}
    assert "R2_WAIT_SHARE" in rule_codes
    assert "R3_REWORK_SHARE" in rule_codes

    dict_repr = report.to_dict()
    assert "total_cycle_minutes" in dict_repr
    assert len(dict_repr["bottlenecks"]) > 0


def test_runbook_5w2h_validator_hygiene():
    valid_steps = [
        RunbookStep(
            step_no=1,
            title="Acknowledge incident",
            owner="On-Call Engineer",
            expected_duration_minutes=2.0,
            success_signal="PagerDuty ticket acknowledged",
            failure_signal="No ack after 2 minutes",
            rollback="n/a (read only acknowledgement)",
            escalation="Operations Lead",
        ),
        RunbookStep(
            step_no=2,
            title="Drain traffic from failing node",
            owner="DevOps Lead",
            expected_duration_minutes=5.0,
            success_signal="Health check returns 0 active connections",
            failure_signal="Connections remain > 0 after 5 min",
            rollback="Re-enable traffic route in consul",
            escalation="VP of Engineering",
        ),
    ]

    report = Runbook5W2HValidator.validate_steps("Incident Drainage Runbook", valid_steps)
    assert report.verdict == "SAFE-TO-USE"
    assert report.hygiene_score == 100.0
    assert report.valid_steps == 2
    assert len(report.must_fix_issues) == 0

    # Bad steps with missing owner & negative duration
    bad_steps = [
        RunbookStep(
            step_no=1,
            title="Do something",
            owner="the team",  # Forbidden
            expected_duration_minutes=-5.0,  # Invalid
            success_signal="",  # Empty
            failure_signal="",
            rollback="",
            escalation="",
        )
    ]
    bad_report = Runbook5W2HValidator.validate_steps("Broken Runbook", bad_steps)
    assert bad_report.verdict == "NOT-SAFE"
    assert bad_report.hygiene_score < 20.0
    assert len(bad_report.must_fix_issues) >= 5


def test_vendor_governance_calculator():
    # 1. Scorecard
    scorecard = VendorGovernanceCalculator.calculate_score(
        vendor_id="v_aws",
        vendor_name="AWS Cloud",
        scores={"delivery": 95.0, "quality": 90.0, "security": 92.0, "support": 85.0},
    )
    assert scorecard.grade == "A"
    assert scorecard.weighted_score >= 90.0

    # 2. SLA Breach
    breach = VendorGovernanceCalculator.track_sla_breach(
        incident_id="inc_001",
        vendor_id="v_aws",
        severity="P1",
        target_mttr_minutes=30.0,
        actual_mttr_minutes=100.0,  # 70 mins breach
        monthly_spend=10000.0,
    )
    assert breach.breach_minutes == 70.0
    assert breach.credit_percentage == 0.15
    assert breach.credit_amount == 1500.0

    # 3. NIST Risk Classification
    tier1 = VendorGovernanceCalculator.classify_risk(
        vendor_id="v_stripe",
        vendor_name="Stripe Payments",
        handles_pii_or_financial_data=True,
        is_direct_production_dependency=True,
        annual_spend=60000.0,
    )
    assert tier1.risk_tier == "TIER_1_CRITICAL"
    assert tier1.break_glass_required is True
    assert tier1.review_cadence_weeks == 4


def test_workforce_capacity_modeler_erlang_c():
    # 60 calls/hour, 5 min handle time => A = 5.0 Erlangs
    plan = WorkforceCapacityModeler.calculate_erlang_c(
        arrival_rate_per_hour=60.0,
        handle_time_minutes=5.0,
        target_wait_seconds=120.0,
        target_service_level=0.80,
    )
    # Recommended headcount must be > 5.0 Erlangs
    assert plan.recommended_headcount >= 6
    assert plan.expected_service_level >= 0.80
    assert 0.0 < plan.utilization_rate <= 1.0

    # 12WY Hiring plan
    demand = [50.0, 55.0, 60.0, 75.0, 90.0, 100.0, 100.0, 95.0, 90.0, 85.0, 80.0, 75.0]
    hiring = WorkforceCapacityModeler.plan_12wy_hiring(
        weekly_arrival_hourly_peak=demand,
        current_headcount=5,
        handle_time_minutes=5.0,
        ramp_weeks=4,
    )
    assert len(hiring) == 12
    assert hiring[0].week_no == 1
    # Check that deficit triggers hire recommendation with lead time
    peak_week = hiring[5]  # Week 6
    assert peak_week.required_headcount > 5
    assert peak_week.headcount_deficit > 0
    assert peak_week.recommended_hire_order_week == 2  # 6 - 4


def test_procurement_spend_analyzer():
    items = [
        SpendItem(
            "Salesforce", "43231500", "CRM", 80000.0, 10, "TIER_1", has_break_glass_plan=True
        ),
        SpendItem("HubSpot", "43231500", "CRM", 15000.0, 3, "TIER_2"),
        SpendItem(
            "Datadog",
            "43232800",
            "Observability",
            50000.0,
            12,
            "TIER_1",
            has_break_glass_plan=False,
        ),
        SpendItem("New Relic", "43232800", "Observability", 20000.0, 5, "TIER_2"),
        SpendItem("GitHub", "43232400", "Dev Tools", 10000.0, 1, "TIER_3"),
    ]

    report = ProcurementSpendAnalyzer.analyze_spend(items)
    assert report.total_spend == 175000.0
    assert len(report.category_breakdown) == 3
    # Salesforce (80k) + HubSpot (15k) = 95k for CRM. Datadog (50k) + New Relic (20k) = 70k.
    assert report.category_breakdown[0].category_name == "CRM"

    # Duplicate tools
    assert "CRM" in report.duplicate_tools_by_category
    assert len(report.duplicate_tools_by_category["CRM"]) == 2
    assert "Observability" in report.duplicate_tools_by_category

    # Single source risk on Datadog
    assert len(report.single_source_tier1_risks) == 1
    assert "Datadog" in report.single_source_tier1_risks[0]
