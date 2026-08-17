"""Pre-ADK imperative implementation of the Sales Pilot pipeline audit.

Mirrors the governance-gated calling pattern already used in
`orchestration/chief_of_staff.py::orchestrate()` (evaluate + audit each tool call
through GovernanceKernel, then invoke the underlying tool function directly), followed
by an LLM synthesis via ModelGateway.

Exists purely as the comparison baseline for `test_adk_and_legacy_sales_parity` in
`test_adk_runtime.py` -- proves the real google-adk Workflow graph in `sales_graph.py`
produces the same structured output as the pre-ADK imperative path for identical inputs.
"""

from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.agents.governance.kernel import GovernanceKernel
from app.agents.reliability.model_gateway import ModelGateway
from app.agents.runtime.types import AgentRunRequest
from app.modules.sales.sales_tools import get_pipeline_summary, list_active_opportunities


async def run_legacy_sales_pilot(
    db: Session,
    workspace_id: int,
    user_id: int,
    goal: str,
    run_id: Optional[int] = None,
    model_profile: str = "reasoning",
) -> Dict[str, Any]:
    """Imperative sales pipeline audit: governance-gated tool calls + LLM synthesis."""
    request = AgentRunRequest(
        company_id=str(workspace_id),
        workspace_id=str(workspace_id),
        user_id=str(user_id),
        agent_key="sales_specialist",
        task=goal,
        permission_profile="read_only",
        parent_run_id=str(run_id) if run_id else None,
    )

    result: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "user_id": user_id,
        "goal": goal,
        "pipeline_summary": {},
        "active_leads": [],
        "synthesis_diagnosis": "",
        "status": "running",
        "error": None,
    }

    try:
        GovernanceKernel.evaluate_and_audit_tool_call(
            db=db, request=request, tool_flat_name="sales_get_pipeline_summary", args={}, run_id=run_id,
        )
        result["pipeline_summary"] = get_pipeline_summary(db, workspace_id)
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = f"Node fetch_pipeline_metrics failed: {exc}"
        return result

    try:
        GovernanceKernel.evaluate_and_audit_tool_call(
            db=db, request=request, tool_flat_name="sales_list_active_opportunities", args={"limit": 10}, run_id=run_id,
        )
        opps = list_active_opportunities(db, workspace_id, limit=10)
        result["active_leads"] = opps.get("opportunities", [])
    except Exception:
        result["active_leads"] = []

    try:
        prompt = (
            f"Analyze sales data for goal: {goal}\n"
            f"Pipeline metrics: {result['pipeline_summary']}\n"
            f"Opportunities: {len(result['active_leads'])} active.\n"
            "Provide brief 2-sentence sales diagnosis."
        )
        gw_result = await ModelGateway.invoke(prompt=prompt, profile_name=model_profile)
        if gw_result.status == "failed":
            raise RuntimeError(gw_result.error)
        result["synthesis_diagnosis"] = gw_result.content
        result["status"] = "completed"
    except Exception:
        result["synthesis_diagnosis"] = f"Fallback sales analysis: {goal}"
        result["status"] = "partial"

    return result
