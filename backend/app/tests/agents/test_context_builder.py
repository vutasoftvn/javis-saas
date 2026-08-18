from unittest.mock import MagicMock, patch
import pytest

from app.workforce.agents.context.builder import build_agent_context
from app.core.snowflake import generate_snowflake_id


def test_build_agent_context_assembles_all_sections():
    mock_db = MagicMock()
    ws_id = generate_snowflake_id()

    with patch("app.workforce.agents.context.builder.get_pipeline_summary", return_value={"status": "success", "metrics": {"total_leads": 42}}), \
         patch("app.workforce.agents.context.builder.get_financial_summary", return_value={"status": "success", "runway_months": 14.5}), \
         patch("app.workforce.agents.context.builder.list_okrs", return_value=[{"id": 1, "name": "Q1 Growth"}]), \
         patch("app.workforce.agents.context.builder.list_projects", return_value=[{"id": 2, "name": "Project Apollo"}]):

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

    with patch("app.workforce.agents.context.builder.get_pipeline_summary", return_value={"status": "success", "metrics": {}}), \
         patch("app.workforce.agents.context.builder.get_financial_summary", side_effect=crashing_finance_tool), \
         patch("app.workforce.agents.context.builder.list_okrs", return_value=[]), \
         patch("app.workforce.agents.context.builder.list_projects", return_value=[]):

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
