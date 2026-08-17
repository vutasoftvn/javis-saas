import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.agents.adk_runtime.adapter import AdkModelAdapter, AdkToolAdapter
from app.agents.adk_runtime.sales_graph import SalesAdkPilotGraph
from app.agents.runtime.types import AgentRunRequest
from app.core.snowflake import generate_snowflake_id


@pytest.mark.asyncio
async def test_adk_model_adapter_delegates_to_model_gateway():
    adapter = AdkModelAdapter(profile_name="chat_fast")
    with patch("app.agents.adk_runtime.adapter.ModelGateway.invoke") as mock_invoke:
        from app.agents.reliability.model_gateway import ModelGatewayResult
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

    with patch("app.agents.adk_runtime.adapter.GovernanceKernel.evaluate_and_audit_tool_call") as mock_gov:
        from app.agents.governance.kernel import GovernanceDecision
        from app.agents.governance.policy_engine import PolicyAction

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
    """Verify parity of structured outputs and governance enforcement between ADK graph and legacy pilot."""
    mock_db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    model_adapter = AdkModelAdapter(profile_name="chat_fast")

    with patch.object(AdkToolAdapter, "call_tool") as mock_call_tool, \
         patch.object(model_adapter, "generate_response", return_value="Strong pipeline momentum."):

        mock_call_tool.side_effect = [
            {"status": "success", "pipeline_metrics": {"lead_count": 10}},
            {"status": "success", "opportunities": [{"id": 1, "company": "Acme Corp"}]},
        ]

        graph = SalesAdkPilotGraph(model_adapter=model_adapter)
        adk_state = await graph.execute(
            db=mock_db,
            workspace_id=ws_id,
            user_id=user_id,
            goal="Q3 Sales Pipeline Audit",
        )

        assert adk_state.status == "completed"
        assert "Strong pipeline momentum" in adk_state.synthesis_diagnosis
        assert len(adk_state.active_leads) == 1
        assert adk_state.workspace_id == ws_id
        assert adk_state.user_id == user_id
