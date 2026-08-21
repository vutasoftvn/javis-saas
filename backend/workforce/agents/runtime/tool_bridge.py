"""Bridge between Agent Runtime, Governance Policy Engine, and Tool Execution."""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from workforce.agents.governance.budget import BudgetTracker
from workforce.agents.governance.models import AgentRun, AgentToolCall
from workforce.agents.governance.policy_engine import PolicyAction
from workforce.agents.runtime.types import AgentRunRequest
from core.snowflake import generate_snowflake_id
from core.tool_bootstrap import load_all_tools
from core.tool_dispatch import execute_tool_spec
from core.tool_registry import get_tool_by_flat_name

logger = logging.getLogger(__name__)
load_all_tools()


async def dispatch_tool_call(
    db: Session,
    request: AgentRunRequest,
    tool_flat_name: str,
    args: dict[str, Any],
    run_id: Optional[int] = None,
) -> dict[str, Any]:
    """Evaluate governance policy via GovernanceKernel and dispatch tool execution."""
    from workforce.agents.governance.kernel import GovernanceKernel, GovernanceDecision

    ws_id = int(request.workspace_id)
    u_id = int(request.user_id) if request.user_id else None
    actual_run_id = int(run_id) if run_id else (int(request.parent_run_id) if request.parent_run_id else None)

    if actual_run_id is not None:
        current_run = (
            db.query(AgentRun)
            .filter(
                AgentRun.id == actual_run_id,
                AgentRun.workspace_id == ws_id,
            )
            .first()
        )
        metadata = current_run.metadata_jsonb if current_run else None
        root_run_id = (
            metadata.get("root_agent_run_id")
            if isinstance(metadata, dict)
            else None
        )
        if root_run_id is not None:
            root_run = (
                db.query(AgentRun)
                .filter(
                    AgentRun.id == int(root_run_id),
                    AgentRun.workspace_id == ws_id,
                )
                .first()
            )
            if root_run is None:
                return {
                    "status": "blocked",
                    "error_code": "ROOT_RUN_NOT_FOUND",
                    "error": "Delegated run root is missing or belongs to another workspace",
                }
            budget_result = BudgetTracker.check_tree(db, root_run)
            if budget_result.is_exceeded:
                return {
                    "status": "blocked",
                    "error_code": budget_result.reason_code or "BUDGET_EXCEEDED",
                    "error": budget_result.message,
                }

    gov_decision: GovernanceDecision = GovernanceKernel.evaluate_and_audit_tool_call(
        db=db,
        request=request,
        tool_flat_name=tool_flat_name,
        args=args,
        run_id=run_id,
    )

    if not gov_decision.allowed:
        if gov_decision.action == PolicyAction.REQUIRE_APPROVAL:
            return {
                "status": "awaiting_approval",
                "approval_id": str(gov_decision.approval.id) if gov_decision.approval else None,
                "tool_name": gov_decision.tool_spec.qualified_name if gov_decision.tool_spec else tool_flat_name,
                "message": gov_decision.reason,
            }
        return {"status": "blocked", "error": gov_decision.reason}

    spec = gov_decision.tool_spec
    if spec is None:
        return {"error": f"Tool '{tool_flat_name}' specification not found."}

    now = datetime.now(timezone.utc)

    # 4. Allowed -> Execute
    t0 = time.perf_counter()
    result = await execute_tool_spec(
        spec=spec,
        db=db,
        workspace_id=ws_id,
        user_id=u_id,
        agent_key=request.agent_key,
        agent_run_id=actual_run_id,
        arguments=args,
        governance_decision=gov_decision,
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    finished_now = datetime.now(timezone.utc)

    is_err = isinstance(result, dict) and "error" in result
    status_str = "error" if is_err else "success"
    out_payload = result if isinstance(result, dict) else {"result": result}

    if actual_run_id:
        record = AgentToolCall(
            id=generate_snowflake_id(),
            run_id=actual_run_id,
            agent_key=request.agent_key,
            tool_name=spec.qualified_name,
            risk_level=spec.risk_level,
            input_jsonb=args,
            output_jsonb=out_payload,
            status=status_str,
            started_at=now,
            finished_at=finished_now,
            latency_ms=latency_ms,
        )
        db.add(record)
        db.commit()

    return out_payload
