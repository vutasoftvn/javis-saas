from sqlalchemy.orm import Session
from typing import Callable, Any
from datetime import datetime, timezone

from app.workforce.tools.invocation.contracts import ToolInvocationRequest, ToolInvocationResult
from app.workforce.agents.governance.kernel import GovernanceKernel, GovernanceDecision
from app.workforce.agents.governance.policy_engine import PolicyAction
from app.workforce.agents.runtime.types import AgentRunRequest

class PolicyGate:
    def __init__(self):
        self.kernel = GovernanceKernel()

    def execute_if_allowed(self, db: Session, request: ToolInvocationRequest, next_step: Callable[..., Any]) -> Any:
        start_time = datetime.now(timezone.utc)
        
        # Map ExecutionScope to AgentRunRequest
        # We synthesize required fields using the invocation context.
        # This prevents models from injecting their own agent_key/mission_id.
        run_request = AgentRunRequest(
            workspace_id=str(request.scope.workspace_id),
            company_id=str(request.scope.company_id),
            user_id=str(request.scope.principal_user_id) if request.scope.principal_user_id else None,
            agent_key=f"system_invocation_{request.source}", # Synthetic agent key
            task=f"Invoke tool {request.tool_flat_name}",
            permission_profile="restricted" # Defaulting to safe profile
        )
        
        decision: GovernanceDecision = self.kernel.evaluate_and_audit_tool_call(
            db=db,
            request=run_request,
            tool_flat_name=request.tool_flat_name,
            args=request.arguments,
            run_id=request.run_id,
        )

        
        if not decision.allowed:
            end_time = datetime.now(timezone.utc)
            latency = int((end_time - start_time).total_seconds() * 1000)
            
            status = "denied"
            approval_id = None
            if decision.action == PolicyAction.REQUIRE_APPROVAL:
                status = "approval_required"
                approval_id = str(decision.approval.id) if decision.approval else None
                
            return ToolInvocationResult(
                correlation_id=request.correlation_id,
                status=status,
                output=None,
                error_message=decision.reason,
                approval_id=approval_id,
                started_at=start_time,
                finished_at=end_time,
                latency_ms=latency
            )
            
        # Allowed! Proceed to dispatch
        return next_step(db, request, decision.tool_spec, decision.sanitized_args)
