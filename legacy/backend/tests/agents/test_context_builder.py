from unittest.mock import MagicMock, patch
import pytest

from workforce.agents.context.builder import build_agent_context
from core.snowflake import generate_snowflake_id
from workforce.agents.governance.kernel import GovernanceDecision
from workforce.agents.governance.policy_engine import PolicyAction


def test_build_agent_context_assembles_all_sections():
    mock_db = MagicMock()
    ws_id = generate_snowflake_id()

    with patch("workforce.agents.context.builder.get_pipeline_summary", return_value={"status": "success", "metrics": {"total_leads": 42}}), \
         patch("workforce.agents.context.builder.get_financial_summary", return_value={"status": "success", "runway_months": 14.5}), \
         patch("workforce.agents.context.builder.list_okrs", return_value=[{"id": 1, "name": "Q1 Growth"}]), \
         patch("workforce.agents.context.builder.list_projects", return_value=[{"id": 2, "name": "Project Apollo"}]):

        context = build_agent_context(
            db=mock_db,
            workspace_id=ws_id,
            company_id=ws_id,
            agent_key="chief_of_staff",
        )

        assert context.workspace_id == str(ws_id)
        assert context.agent_key == "chief_of_staff"
        assert set(context.sections.keys()) == {"sales", "finance", "okrs", "projects"}

        # Check freshness and data
        sales_sec = context.sections["sales"]
        assert sales_sec.status == "success"
        assert sales_sec.data["metrics"]["total_leads"] == 42
        assert sales_sec.fetched_at is not None

        fin_sec = context.sections["finance"]
        assert fin_sec.status == "success"
        assert fin_sec.data["runway_months"] == 14.5

        okr_sec = context.sections["okrs"]
        assert okr_sec.status == "success"
        assert len(okr_sec.data["result"]) == 1


def test_build_agent_context_graceful_degradation_on_tool_failure():
    mock_db = MagicMock()
    ws_id = generate_snowflake_id()

    def crashing_finance_tool(*args, **kwargs):
        raise RuntimeError("Database connection timed out")

    with patch("workforce.agents.context.builder.get_pipeline_summary", return_value={"status": "success", "metrics": {}}), \
         patch("workforce.agents.context.builder.get_financial_summary", side_effect=crashing_finance_tool), \
         patch("workforce.agents.context.builder.list_okrs", return_value=[]), \
         patch("workforce.agents.context.builder.list_projects", return_value=[]):

        # Context build should NOT raise exception despite finance tool crashing
        context = build_agent_context(
            db=mock_db,
            workspace_id=ws_id,
            agent_key="chief_of_staff",
        )

        assert context.sections["sales"].status == "success"
        fin_sec = context.sections["finance"]
        assert fin_sec.status == "error"
        assert "Database connection timed out" in (fin_sec.error or "")
        assert fin_sec.data == {}


def test_build_agent_context_governance_denial_blocks_fetch():
    """Regression test: a GovernanceKernel denial must actually block the fetch,
    not just be logged. Previously the returned GovernanceDecision was discarded
    and the fetcher always ran regardless of `allowed`."""
    mock_db = MagicMock()
    ws_id = generate_snowflake_id()

    def governance_side_effect(db, request, tool_flat_name, args):
        if tool_flat_name == "sales_get_pipeline_summary":
            return GovernanceDecision(allowed=False, action=PolicyAction.DENY, reason="quota exceeded")
        return GovernanceDecision(allowed=True, action=PolicyAction.ALLOW, reason="ok")

    with patch(
        "workforce.agents.context.builder.GovernanceKernel.evaluate_and_audit_tool_call",
        side_effect=governance_side_effect,
    ), patch(
        "workforce.agents.context.builder.get_pipeline_summary"
    ) as mock_pipeline, \
         patch("workforce.agents.context.builder.get_financial_summary", return_value={"status": "success", "runway_months": 1}), \
         patch("workforce.agents.context.builder.list_okrs", return_value=[]), \
         patch("workforce.agents.context.builder.list_projects", return_value=[]):

        context = build_agent_context(
            db=mock_db,
            workspace_id=ws_id,
            agent_key="chief_of_staff",
        )

        sales_sec = context.sections["sales"]
        assert sales_sec.status == "error"
        assert "quota exceeded" in (sales_sec.error or "")
        assert sales_sec.data == {}
        mock_pipeline.assert_not_called()

        # Other sections, not denied, still fetch normally.
        assert context.sections["finance"].status == "success"
