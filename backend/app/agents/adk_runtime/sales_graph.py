"""Sales Pilot Graph using Google ADK 2.0 graph workflow paradigm for COSA OS.

Encapsulates the Sales Research and Pipeline Investigation workflow into graph nodes:
1. Node: fetch_pipeline_metrics (via AdkToolAdapter / GovernanceKernel)
2. Node: filter_high_fit_leads
3. Node: synthesize_sales_diagnosis (via AdkModelAdapter / ModelGateway)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.adk_runtime.adapter import AdkModelAdapter, AdkToolAdapter
from app.agents.runtime.types import AgentRunRequest


class SalesPilotGraphState(BaseModel):
    workspace_id: int
    user_id: int
    goal: str
    pipeline_summary: Dict[str, Any] = Field(default_factory=dict)
    active_leads: List[Dict[str, Any]] = Field(default_factory=list)
    synthesis_diagnosis: str = ""
    status: str = "running"
    error: Optional[str] = None


class SalesAdkPilotGraph:
    """Graph workflow executor for Sales Pilot domain."""

    def __init__(self, model_adapter: Optional[AdkModelAdapter] = None):
        self.model_adapter = model_adapter or AdkModelAdapter(profile_name="reasoning")

    async def execute(
        self,
        db: Session,
        workspace_id: int,
        user_id: int,
        goal: str,
        run_id: Optional[int] = None,
    ) -> SalesPilotGraphState:
        state = SalesPilotGraphState(
            workspace_id=workspace_id,
            user_id=user_id,
            goal=goal,
        )

        request = AgentRunRequest(
            company_id=str(workspace_id),
            workspace_id=str(workspace_id),
            user_id=str(user_id),
            agent_key="sales_specialist",
            task=goal,
            permission_profile="read_only",
            parent_run_id=str(run_id) if run_id else None,
        )

        # Node 1: Fetch pipeline metrics via AdkToolAdapter
        try:
            metrics_res = await AdkToolAdapter.call_tool(
                db=db,
                request=request,
                tool_flat_name="sales_get_pipeline_summary",
                arguments={},
                run_id=run_id,
            )
            state.pipeline_summary = metrics_res
        except Exception as exc:
            state.status = "failed"
            state.error = f"Node fetch_pipeline_metrics failed: {exc}"
            return state

        # Node 2: Extract active opportunities
        try:
            opps_res = await AdkToolAdapter.call_tool(
                db=db,
                request=request,
                tool_flat_name="sales_list_active_opportunities",
                arguments={"limit": 10},
                run_id=run_id,
            )
            state.active_leads = opps_res.get("opportunities", [])
        except Exception as exc:
            state.active_leads = []

        # Node 3: Synthesize sales diagnosis via AdkModelAdapter
        try:
            prompt = (
                f"Analyze sales data for goal: {goal}\n"
                f"Pipeline metrics: {state.pipeline_summary}\n"
                f"Opportunities: {len(state.active_leads)} active.\n"
                "Provide brief 2-sentence sales diagnosis."
            )
            synthesis = await self.model_adapter.generate_response(prompt)
            state.synthesis_diagnosis = synthesis
            state.status = "completed"
        except Exception as exc:
            state.synthesis_diagnosis = f"Fallback sales analysis: {goal}"
            state.status = "partial"

        return state
