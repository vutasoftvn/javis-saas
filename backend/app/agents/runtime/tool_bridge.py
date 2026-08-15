"""Bridge between Agent Runtime, Governance Policy Engine, and Tool Execution."""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.agents.governance.approval_service import ApprovalService
from app.agents.governance.models import AgentToolCall
from app.agents.governance.policy_engine import PolicyAction, PolicyEngine
from app.agents.runtime.types import AgentRunRequest
from app.core.snowflake import generate_snowflake_id
from app.core.tool_bootstrap import load_all_tools
from app.core.tool_dispatch import execute_tool_spec
from app.core.tool_registry import get_tool_by_flat_name

logger = logging.getLogger(__name__)
load_all_tools()


async def dispatch_tool_call(
    db: Session,
    request: AgentRunRequest,
    tool_flat_name: str,
    args: dict[str, Any],
    run_id: Optional[int] = None,
) -> dict[str, Any]:
    """Evaluate governance policy and dispatch tool execution.

    Enforces:
    1. Tool existence check.
    2. PolicyEngine L0-L3 permission check & agent key whitelist.
    3. Approval creation if required (pauses execution).
    4. Safe parameter-injected tool execution if allowed.
    5. Postgres audit logging via AgentToolCall record.
    """
    spec = get_tool_by_flat_name(tool_flat_name)
    if spec is None:
        return {"error": f"Tool '{tool_flat_name}' is not registered in the system."}

    ws_id = int(request.workspace_id)
    u_id = int(request.user_id) if request.user_id else None
    c_id = int(request.company_id) if request.company_id else None
    actual_run_id = int(run_id) if run_id else (int(request.parent_run_id) if request.parent_run_id else None)

    # 1. Policy Evaluation
    decision = PolicyEngine.evaluate(
        agent_key=request.agent_key,
        tool_spec=spec,
        permission_profile=request.permission_profile,
        input_data=args,
    )

    now = datetime.now(timezone.utc)

    # 2. Denied
    if decision.action == PolicyAction.DENY:
        if actual_run_id:
            record = AgentToolCall(
                id=generate_snowflake_id(),
                run_id=actual_run_id,
                agent_key=request.agent_key,
                tool_name=spec.qualified_name,
                risk_level=spec.risk_level,
                input_jsonb=args,
                output_jsonb={"error": decision.reason},
                status="blocked",
                started_at=now,
                finished_at=now,
                latency_ms=0,
            )
            db.add(record)
            db.commit()
        return {"status": "blocked", "error": decision.reason}

    # 3. Requires Human Approval
    if decision.action == PolicyAction.REQUIRE_APPROVAL:
        approval = ApprovalService.create_approval(
            db=db,
            workspace_id=ws_id,
            company_id=c_id,
            agent_key=request.agent_key,
            action_type="tool_execution",
            tool_name=spec.qualified_name,
            input_preview=args,
            risk_level=spec.risk_level,
            run_id=actual_run_id,
        )
        if actual_run_id:
            record = AgentToolCall(
                id=generate_snowflake_id(),
                run_id=actual_run_id,
                agent_key=request.agent_key,
                tool_name=spec.qualified_name,
                risk_level=spec.risk_level,
                input_jsonb=args,
                output_jsonb={"approval_id": str(approval.id), "status": "pending"},
                status="approval_pending",
                approval_id=approval.id,
                started_at=now,
                finished_at=now,
                latency_ms=0,
            )
            db.add(record)
            db.commit()
        return {
            "status": "awaiting_approval",
            "approval_id": str(approval.id),
            "tool_name": spec.qualified_name,
            "message": decision.reason,
        }

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
