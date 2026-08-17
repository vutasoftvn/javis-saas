"""Sales Pilot Graph using the real Google ADK 2.0 Workflow/Node graph engine for COSA OS.

Builds a `google.adk.workflow.Workflow` (real SDK graph orchestration — node scheduling,
session state, event stream all handled by google-adk, not hand-rolled Python control
flow) with 3 nodes:
1. Node: fetch_pipeline_metrics (via AdkToolAdapter / GovernanceKernel)
2. Node: fetch_active_opportunities (via AdkToolAdapter / GovernanceKernel)
3. Node: synthesize_sales_diagnosis (via AdkModelAdapter / ModelGateway)
"""

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from google.adk.workflow import Workflow, node, START
from google.adk.agents.context import Context
from google.adk.runners import InMemoryRunner
from google.genai import types

from app.agents.adk_runtime.adapter import AdkModelAdapter, AdkToolAdapter
from app.agents.runtime.types import AgentRunRequest


class SalesPilotGraphState(BaseModel):
    workspace_id: int = 0
    user_id: int = 0
    goal: str = ""
    pipeline_summary: Dict[str, Any] = Field(default_factory=dict)
    active_leads: List[Dict[str, Any]] = Field(default_factory=list)
    synthesis_diagnosis: str = ""
    status: str = "running"
    error: Optional[str] = None


class SalesAdkPilotGraph:
    """Graph workflow executor for Sales Pilot domain, backed by a real google-adk Workflow."""

    def __init__(self, model_adapter: Optional[AdkModelAdapter] = None):
        self.model_adapter = model_adapter or AdkModelAdapter(profile_name="reasoning")

    def _build_workflow(
        self,
        db: Session,
        request: AgentRunRequest,
        run_id: Optional[int],
    ) -> Workflow:
        async def fetch_pipeline_metrics(ctx: Context) -> None:
            try:
                res = await AdkToolAdapter.call_tool(
                    db=db,
                    request=request,
                    tool_flat_name="sales_get_pipeline_summary",
                    arguments={},
                    run_id=run_id,
                )
                ctx.state["pipeline_summary"] = res
            except Exception as exc:
                ctx.state["status"] = "failed"
                ctx.state["error"] = f"Node fetch_pipeline_metrics failed: {exc}"

        async def fetch_active_opportunities(ctx: Context) -> None:
            if ctx.state.get("status") == "failed":
                return
            try:
                res = await AdkToolAdapter.call_tool(
                    db=db,
                    request=request,
                    tool_flat_name="sales_list_active_opportunities",
                    arguments={"limit": 10},
                    run_id=run_id,
                )
                ctx.state["active_leads"] = res.get("opportunities", [])
            except Exception:
                ctx.state["active_leads"] = []

        async def synthesize_sales_diagnosis(ctx: Context) -> None:
            if ctx.state.get("status") == "failed":
                return
            try:
                prompt = (
                    f"Analyze sales data for goal: {ctx.state['goal']}\n"
                    f"Pipeline metrics: {ctx.state['pipeline_summary']}\n"
                    f"Opportunities: {len(ctx.state['active_leads'])} active.\n"
                    "Provide brief 2-sentence sales diagnosis."
                )
                synthesis = await self.model_adapter.generate_response(prompt)
                ctx.state["synthesis_diagnosis"] = synthesis
                ctx.state["status"] = "completed"
            except Exception:
                ctx.state["synthesis_diagnosis"] = f"Fallback sales analysis: {ctx.state['goal']}"
                ctx.state["status"] = "partial"

        n1 = node(fetch_pipeline_metrics, name="fetch_pipeline_metrics")
        n2 = node(fetch_active_opportunities, name="fetch_active_opportunities")
        n3 = node(synthesize_sales_diagnosis, name="synthesize_sales_diagnosis")

        return Workflow(
            name="sales_pilot_graph",
            edges=[(START, n1, n2, n3)],
            state_schema=SalesPilotGraphState,
        )

    async def execute(
        self,
        db: Session,
        workspace_id: int,
        user_id: int,
        goal: str,
        run_id: Optional[int] = None,
    ) -> SalesPilotGraphState:
        request = AgentRunRequest(
            company_id=str(workspace_id),
            workspace_id=str(workspace_id),
            user_id=str(user_id),
            agent_key="sales_specialist",
            task=goal,
            permission_profile="read_only",
            parent_run_id=str(run_id) if run_id else None,
        )

        workflow = self._build_workflow(db=db, request=request, run_id=run_id)
        app_name = "sales_pilot_graph"
        session_user_id = str(user_id)
        session_id = str(run_id) if run_id else uuid.uuid4().hex

        runner = InMemoryRunner(node=workflow, app_name=app_name)
        await runner.session_service.create_session(
            app_name=app_name,
            user_id=session_user_id,
            session_id=session_id,
            state={"workspace_id": workspace_id, "user_id": user_id, "goal": goal},
        )

        async for _event in runner.run_async(
            user_id=session_user_id,
            session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part(text=goal)]),
        ):
            pass

        final_session = await runner.session_service.get_session(
            app_name=app_name, user_id=session_user_id, session_id=session_id
        )
        return SalesPilotGraphState.model_validate(final_session.state)
