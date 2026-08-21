"""Governance Kernel for COSA OS (§P0.5, C1/C2 Spec).

Acts as the unified gateway and policy facade for tool execution, secret brokering,
risk gate evaluation, and audit trail generation across the agent runtime.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from workforce.agents.execution.credential_broker import CredentialBroker
from workforce.agents.governance.approval_service import ApprovalService
from workforce.agents.governance.models import AgentApproval, AgentEventRecord, AgentToolCall
from workforce.agents.governance.policy_engine import PolicyAction, PolicyDecision, PolicyEngine
from workforce.agents.runtime.types import AgentRunRequest
from core.snowflake import generate_snowflake_id
from core.telemetry import trace_span
from core.tool_registry import ToolSpec, get_tool_by_flat_name

logger = logging.getLogger(__name__)


@dataclass
class GovernanceDecision:
    allowed: bool
    action: PolicyAction
    reason: str
    tool_spec: Optional[ToolSpec] = None
    approval: Optional[AgentApproval] = None
    sanitized_args: Optional[dict[str, Any]] = None


class GovernanceKernel:
    """Unified Facade for Governance, Tool Sentinel, Secret Brokering, and Audit Logging."""

    @classmethod
    def evaluate_and_audit_tool_call(
        cls,
        db: Session,
        request: AgentRunRequest,
        tool_flat_name: str,
        args: dict[str, Any],
        run_id: Optional[int] = None,
    ) -> GovernanceDecision:
        """Inspect and evaluate a tool call request before execution."""
        with trace_span("governance_kernel.evaluate", {"tool": tool_flat_name, "agent_key": request.agent_key}):
            return cls._evaluate_and_audit_internal(db, request, tool_flat_name, args, run_id)

    @classmethod
    def _evaluate_and_audit_internal(
        cls,
        db: Session,
        request: AgentRunRequest,
        tool_flat_name: str,
        args: dict[str, Any],
        run_id: Optional[int] = None,
    ) -> GovernanceDecision:
        spec = get_tool_by_flat_name(tool_flat_name)
        if spec is None:
            return GovernanceDecision(
                allowed=False,
                action=PolicyAction.DENY,
                reason=f"Tool '{tool_flat_name}' is not registered in the system.",
            )

        ws_id = int(request.workspace_id)
        u_id = int(request.user_id) if request.user_id else None
        c_id = int(request.company_id) if request.company_id else None
        actual_run_id = int(run_id) if run_id else (int(request.parent_run_id) if request.parent_run_id else None)
        now = datetime.now(timezone.utc)

        # 1. Policy Evaluation
        policy_decision: PolicyDecision = PolicyEngine.evaluate(
            agent_key=request.agent_key,
            tool_spec=spec,
            permission_profile=request.permission_profile,
            input_data=args,
        )

        # 2. Denied
        if policy_decision.action == PolicyAction.DENY:
            if actual_run_id:
                record = AgentToolCall(
                    id=generate_snowflake_id(),
                    run_id=actual_run_id,
                    agent_key=request.agent_key,
                    tool_name=spec.qualified_name,
                    risk_level=spec.risk_level,
                    input_jsonb=args,
                    output_jsonb={"error": policy_decision.reason},
                    status="blocked",
                    started_at=now,
                    finished_at=now,
                    latency_ms=0,
                )
                db.add(record)
                db.commit()
            return GovernanceDecision(
                allowed=False,
                action=PolicyAction.DENY,
                reason=policy_decision.reason,
                tool_spec=spec,
                sanitized_args=args,
            )

        # 3. Requires Human Approval
        if policy_decision.action == PolicyAction.REQUIRE_APPROVAL or spec.requires_approval:
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
            return GovernanceDecision(
                allowed=False,
                action=PolicyAction.REQUIRE_APPROVAL,
                reason=policy_decision.reason or "Action requires human approval",
                tool_spec=spec,
                approval=approval,
                sanitized_args=args,
            )

        # 4. Allowed -> Sanitize / prepare args
        return GovernanceDecision(
            allowed=True,
            action=PolicyAction.ALLOW,
            reason=policy_decision.reason or "Action authorized by Governance Policy",
            tool_spec=spec,
            sanitized_args=args,
        )
