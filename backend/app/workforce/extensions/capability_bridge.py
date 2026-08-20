from sqlalchemy.orm import Session

from app.workforce.agents.governance.kernel import GovernanceDecision, GovernanceKernel
from app.workforce.agents.governance.policy_engine import PolicyAction
from app.workforce.agents.runtime.execution_scope import ExecutionScope
from app.workforce.agents.runtime.types import AgentRunRequest
from app.workforce.extensions.seams import (
    ConnectorProvider,
    DiscoveredCapability,
    ProviderResult,
)
from app.workforce.tools.invocation.contracts import ToolInvocationRequest


class CapabilityBridge:
    async def invoke(
        self,
        db: Session,
        scope: ExecutionScope,
        request: ToolInvocationRequest,
        run_id: int | None,
        capability: DiscoveredCapability,
        provider: ConnectorProvider,
        decision: GovernanceDecision | None = None,
    ) -> ProviderResult | dict:
        if decision is None:
            decision = GovernanceKernel.evaluate_and_audit_tool_call(
                db=db,
                request=_agent_run_request(request),
                tool_flat_name=request.tool_flat_name,
                args=request.arguments,
                run_id=run_id,
            )

        if decision.action == PolicyAction.DENY:
            return {"status": "blocked", "error": decision.reason}

        if decision.action == PolicyAction.REQUIRE_APPROVAL:
            return {
                "status": "awaiting_approval",
                "approval_id": str(decision.approval.id) if decision.approval else None,
                "tool_name": (
                    decision.tool_spec.qualified_name
                    if decision.tool_spec
                    else request.tool_flat_name
                ),
                "message": decision.reason,
            }

        arguments = (
            decision.sanitized_args
            if decision.sanitized_args is not None
            else request.arguments
        )
        return await provider.invoke(scope, capability, arguments)


def _agent_run_request(request: ToolInvocationRequest) -> AgentRunRequest:
    return AgentRunRequest(
        workspace_id=str(request.scope.workspace_id),
        company_id=str(request.scope.company_id),
        user_id=str(request.scope.principal_user_id),
        agent_key=f"system_invocation_{request.source}",
        task=f"Invoke tool {request.tool_flat_name}",
        permission_profile="restricted",
    )
