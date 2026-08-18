import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.workforce.agents.adk_runtime.adapter import AdkModelAdapter, AdkToolAdapter
from app.workforce.agents.adk_runtime.legacy_sales_pilot import run_legacy_sales_pilot
from app.workforce.agents.adk_runtime.sales_graph import SalesAdkPilotGraph
from app.workforce.agents.runtime.types import AgentRunRequest
from app.core.snowflake import generate_snowflake_id


@pytest.mark.asyncio
async def test_adk_model_adapter_delegates_to_model_gateway():
    adapter = AdkModelAdapter(profile_name="chat_fast")
    with patch("app.workforce.agents.adk_runtime.adapter.ModelGateway.invoke") as mock_invoke:
        from app.workforce.agents.reliability.model_gateway import ModelGatewayResult
        mock_invoke.return_value = ModelGatewayResult(
            content="Simulated ADK LLM output",
            provider="deepseek",
            model="deepseek-chat",
            status="success",
        )

        res = await adapter.generate_response("Test prompt")
        assert res == "Simulated ADK LLM output"
        mock_invoke.assert_called_once()


@pytest.mark.asyncio
async def test_adk_tool_adapter_enforces_governance_kernel():
    mock_db = MagicMock()
    req = AgentRunRequest(
        company_id="1",
        workspace_id="1",
        user_id="1",
        agent_key="sales_specialist",
        task="Test task",
        permission_profile="read_only",
    )

    with patch("app.workforce.agents.adk_runtime.adapter.GovernanceKernel.evaluate_and_audit_tool_call") as mock_gov:
        from app.workforce.agents.governance.kernel import GovernanceDecision
        from app.workforce.agents.governance.policy_engine import PolicyAction

        mock_gov.return_value = GovernanceDecision(
            allowed=False,
            action=PolicyAction.DENY,
            reason="Action denied by policy",
        )

        res = await AdkToolAdapter.call_tool(
            db=mock_db,
            request=req,
            tool_flat_name="sales_get_pipeline_summary",
            arguments={},
        )
        assert res["status"] == "denied"
        assert "denied by policy" in res["reason"]


@pytest.mark.asyncio
async def test_adk_sales_pilot_graph_execution():
    mock_db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    model_adapter = AdkModelAdapter(profile_name="chat_fast")

    with patch.object(AdkToolAdapter, "call_tool") as mock_call_tool, \
         patch.object(model_adapter, "generate_response", return_value="Pipeline is healthy."):

        mock_call_tool.side_effect = [
            {"status": "success", "metrics": {"qualified_leads": 5}},
            {"status": "success", "opportunities": [{"id": 1, "product": "COSA Platform"}]},
        ]

        graph = SalesAdkPilotGraph(model_adapter=model_adapter)
        state = await graph.execute(
            db=mock_db,
            workspace_id=ws_id,
            user_id=user_id,
            goal="Analyze Sales Pipeline for Q3",
        )

        assert state.status == "completed"
        assert state.synthesis_diagnosis == "Pipeline is healthy."
        assert len(state.active_leads) == 1
        assert state.pipeline_summary["status"] == "success"


@pytest.mark.asyncio
async def test_adk_and_legacy_sales_parity():
    """Verify the real ADK Workflow graph and the pre-ADK imperative path produce
    identical structured output given identical mocked tool/model responses.

    This is a genuine parity test: both code paths run independently against the
    same fixtures, and their final outputs are diffed -- unlike the old version,
    which only ever exercised the ADK path and asserted on its own mocked output.
    """
    mock_db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    run_id = generate_snowflake_id()
    goal = "Q3 Sales Pipeline Audit"

    pipeline_fixture = {"status": "success", "metrics": {"qualified_leads": 5}}
    opportunities_fixture = {"status": "success", "opportunities": [{"id": 1, "product": "Acme Corp"}]}
    synthesis_text = "Strong pipeline momentum."

    # --- Run the real ADK Workflow graph path ---
    adk_model_adapter = AdkModelAdapter(profile_name="chat_fast")
    with patch.object(AdkToolAdapter, "call_tool") as mock_call_tool, \
         patch.object(adk_model_adapter, "generate_response", return_value=synthesis_text):
        mock_call_tool.side_effect = [pipeline_fixture, opportunities_fixture]

        graph = SalesAdkPilotGraph(model_adapter=adk_model_adapter)
        adk_state = await graph.execute(
            db=mock_db, workspace_id=ws_id, user_id=user_id, goal=goal, run_id=run_id,
        )

    # --- Run the pre-ADK legacy imperative path with the SAME fixtures ---
    with patch("app.workforce.agents.adk_runtime.legacy_sales_pilot.GovernanceKernel.evaluate_and_audit_tool_call"), \
         patch("app.workforce.agents.adk_runtime.legacy_sales_pilot.get_pipeline_summary", return_value=pipeline_fixture), \
         patch("app.workforce.agents.adk_runtime.legacy_sales_pilot.list_active_opportunities", return_value=opportunities_fixture), \
         patch("app.workforce.agents.adk_runtime.legacy_sales_pilot.ModelGateway.invoke", new_callable=AsyncMock) as mock_invoke:
        from app.workforce.agents.reliability.model_gateway import ModelGatewayResult
        mock_invoke.return_value = ModelGatewayResult(
            content=synthesis_text, provider="deepseek", model="deepseek-chat", status="success",
        )

        legacy_result = await run_legacy_sales_pilot(
            db=mock_db, workspace_id=ws_id, user_id=user_id, goal=goal, run_id=run_id,
        )

    # --- Parity assertions: both paths must produce the same structured output ---
    assert adk_state.status == legacy_result["status"] == "completed"
    assert adk_state.pipeline_summary == legacy_result["pipeline_summary"] == pipeline_fixture
    assert adk_state.active_leads == legacy_result["active_leads"] == opportunities_fixture["opportunities"]
    assert adk_state.synthesis_diagnosis == legacy_result["synthesis_diagnosis"] == synthesis_text
