from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock
import pytest

from core.snowflake import generate_snowflake_id
from core.tool_registry import get_registered_tools
from business.sales.models import SalesLead, SalesOpportunity
from business.sales.sales_tools import (
    get_pipeline_summary,
    get_lead_details,
    list_active_opportunities,
)
from business.finance.models import AccountingProfile, AccountingPeriod, FinanceManagementSnapshot
from business.finance.finance_tools import (
    get_financial_summary,
    get_period_overview,
)


def test_sales_and_finance_tools_have_governance_metadata():
    tools = get_registered_tools()

    # Sales tools
    assert "sales.get_pipeline_summary" in tools
    sales_pipeline = tools["sales.get_pipeline_summary"]
    assert sales_pipeline.permission_level == "read_only"
    assert sales_pipeline.risk_level == "low"
    assert sales_pipeline.requires_approval is False
    assert sales_pipeline.idempotency is True
    assert "sales_specialist" in sales_pipeline.allowed_agent_keys

    # Finance tools
    assert "finance.get_financial_summary" in tools
    fin_summary = tools["finance.get_financial_summary"]
    assert fin_summary.permission_level == "read_only"
    assert fin_summary.risk_level == "low"
    assert fin_summary.requires_approval is False
    assert fin_summary.idempotency is True
    assert "finance_specialist" in fin_summary.allowed_agent_keys


def test_sales_agent_poc_pipeline_and_lead_details(monkeypatch):
    ws_id = generate_snowflake_id()

    # Mock FunnelMetricsService output
    mock_metrics = {
        "total_leads": 5,
        "qualified_leads": 3,
        "converted_leads": 1,
        "total_opportunities": 4,
        "won_opportunities": 2,
        "pipeline_value": 45000000.0,
    }
    monkeypatch.setattr(
        "business.sales.sales_tools.FunnelMetricsService.get_funnel_metrics",
        lambda db, workspace_id: mock_metrics,
    )

    db = MagicMock()

    # 1. Test get_pipeline_summary
    pipeline_res = get_pipeline_summary(db, ws_id)
    assert pipeline_res["status"] == "success"
    assert pipeline_res["metrics"]["total_leads"] == 5
    assert pipeline_res["metrics"]["pipeline_value"] == 45000000.0

    # 2. Test get_lead_details
    lead = SalesLead(
        id=101,
        workspace_id=ws_id,
        name="Enterprise Deal Alpha",
        company="Alpha Corp",
        stage="NEW",
        qualification_status="QUALIFIED",
        fit_score=85.0,
        value=50000000.0,
        source="website",
    )
    db.query.return_value.filter.return_value.first.return_value = lead

    lead_res = get_lead_details(db, ws_id, 101)
    assert lead_res["status"] == "success"
    assert lead_res["lead"]["name"] == "Enterprise Deal Alpha"
    assert lead_res["lead"]["company"] == "Alpha Corp"
    assert lead_res["lead"]["fit_score"] == 85.0
    assert lead_res["lead"]["qualification_status"] == "QUALIFIED"

    # 3. Test list_active_opportunities
    opp1 = SalesOpportunity(
        id=201,
        workspace_id=ws_id,
        account_id=generate_snowflake_id(),
        product="Alpha Cloud Deployment",
        stage="PROPOSAL",
        estimated_value=45000000.0,
    )
    db.query.return_value.filter.return_value.limit.return_value.all.return_value = [opp1]

    opps_res = list_active_opportunities(db, ws_id)
    assert opps_res["status"] == "success"
    assert opps_res["total"] == 1
    assert opps_res["opportunities"][0]["product"] == "Alpha Cloud Deployment"


def test_sales_tools_tenant_isolation():
    ws_b = generate_snowflake_id()
    db = MagicMock()
    # Mocking query returning None when querying cross-tenant
    db.query.return_value.filter.return_value.first.return_value = None

    cross_res = get_lead_details(db, ws_b, 999)
    assert cross_res["status"] == "not_found"


def test_finance_agent_poc_summary_and_period():
    ws_id = generate_snowflake_id()
    db = MagicMock()

    profile = AccountingProfile(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        mode="TT58_MODE_1",
        status="CONFIRMED",
    )
    snapshot = FinanceManagementSnapshot(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        as_of=date(2026, 8, 1),
        cash=Decimal("1500000000"),
        burn=Decimal("120000000"),
        runway_months=Decimal("12.5"),
        revenue=Decimal("200000000"),
        expenses=Decimal("120000000"),
        budget_variance=Decimal("10000000"),
    )
    period = AccountingPeriod(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 9, 30),
        status="OPEN",
    )

    def query_mock(model):
        m = MagicMock()
        m.filter.return_value = m
        m.order_by.return_value = m
        if model == AccountingProfile:
            m.first.return_value = profile
        elif model == FinanceManagementSnapshot:
            m.first.return_value = snapshot
        elif model == AccountingPeriod:
            m.all.return_value = [period]
        return m

    db.query.side_effect = query_mock

    # 1. Test get_financial_summary
    fin_res = get_financial_summary(db, ws_id)
    assert fin_res["status"] == "success"
    assert fin_res["profile_mode"] == "TT58_MODE_1"
    assert fin_res["profile_status"] == "CONFIRMED"
    assert fin_res["cash_balance"] > 0
    assert fin_res["runway_months"] is not None

    # 2. Test get_period_overview
    period_res = get_period_overview(db, ws_id)
    assert period_res["status"] == "success"
    assert period_res["total_periods"] == 1
    assert period_res["periods"][0]["status"] == "OPEN"
    assert period_res["periods"][0]["start_date"] == "2026-07-01"


def test_finance_agent_poc_summary_not_configured_without_snapshot():
    ws_id = generate_snowflake_id()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    fin_res = get_financial_summary(db, ws_id)
    assert fin_res["status"] == "not_configured"
    assert "cash_balance" not in fin_res
