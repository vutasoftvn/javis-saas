"""ADK Model and Tool Adapters for COSA OS.

Decouples Google ADK graph nodes from direct SDK dependencies, ensuring:
1. All LLM calls pass through ModelGateway (retry, circuit-breaker, fallback).
2. All Tool invocations pass through GovernanceKernel (policy, approval, audit).
"""

from typing import Any, Callable, Dict, Optional
from sqlalchemy.orm import Session

from app.workforce.agents.governance.kernel import GovernanceKernel, GovernanceDecision
from app.workforce.agents.reliability.model_gateway import ModelGateway, ModelGatewayResult
from app.workforce.agents.runtime.types import AgentRunRequest
from app.core.tool_dispatch import execute_tool_spec


class AdkModelAdapter:
    """Adapts Google ADK model interface to COSA ModelGateway."""

    def __init__(self, profile_name: str = "chat_fast", system_instruction: Optional[str] = None):
        self.profile_name = profile_name
        self.system_instruction = system_instruction

    async def generate_response(self, prompt: str) -> str:
        """Invokes ModelGateway with the configured profile."""
        result: ModelGatewayResult = await ModelGateway.invoke(
            prompt=prompt,
            profile_name=self.profile_name,
            system_instruction=self.system_instruction,
        )
        if result.status == "failed":
            raise RuntimeError(f"ADK Model Invocation Failed: {result.error}")
        return result.content


class AdkToolAdapter:
    """Adapts ADK tool node calls to go strictly through GovernanceKernel and execute_tool_spec."""

    @staticmethod
    async def call_tool(
        db: Session,
        request: AgentRunRequest,
        tool_flat_name: str,
        arguments: Dict[str, Any],
        run_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Evaluates governance policy and executes the tool."""
        decision: GovernanceDecision = GovernanceKernel.evaluate_and_audit_tool_call(
            db=db,
            request=request,
            tool_flat_name=tool_flat_name,
            args=arguments,
            run_id=run_id,
        )

        if not decision.allowed:
            return {
                "status": "denied" if decision.action.value != "require_approval" else "awaiting_approval",
                "action": decision.action.value,
                "reason": decision.reason,
                "approval_id": str(decision.approval.id) if decision.approval else None,
            }

        spec = decision.tool_spec
        if not spec:
            return {"status": "error", "error": f"Tool spec '{tool_flat_name}' not found."}

        ws_id = int(request.workspace_id)
        user_id = int(request.user_id) if request.user_id else None

        result = await execute_tool_spec(
            spec=spec,
            db=db,
            workspace_id=ws_id,
            user_id=user_id,
            agent_key=request.agent_key,
            agent_run_id=run_id,
            arguments=arguments,
        )
        return result if isinstance(result, dict) else {"result": result}
