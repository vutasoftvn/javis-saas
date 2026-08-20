from sqlalchemy.orm import Session
from typing import Any, Dict
from datetime import datetime, timezone
import asyncio
import logging

from app.core.tool_registry import ToolSpec
from app.workforce.tools.invocation.contracts import ToolInvocationRequest, ToolInvocationResult, ToolInvocationError
from app.workforce.tools.invocation.input_validation import normalize_arguments, InputValidationError
from app.workforce.tools.invocation.policy_gate import PolicyGate
from app.workforce.tools.invocation.dispatchers import NativeDispatcher
from app.workforce.tools.invocation.output_safety import format_output
from app.workforce.agents.runtime.execution_scope import ExecutionScope

logger = logging.getLogger(__name__)

class ToolInvocationService:
    def __init__(self):
        self.policy_gate = PolicyGate()
        self.native_dispatcher = NativeDispatcher()

    async def invoke(self, db: Session, request: ToolInvocationRequest) -> ToolInvocationResult:
        try:
            # We need the spec first.
            # get_tool_by_flat_name is used in PolicyGate, but we also need it for input validation
            from app.core.tool_registry import get_tool_by_flat_name
            spec = get_tool_by_flat_name(request.tool_flat_name)
            if not spec:
                return ToolInvocationResult(
                    correlation_id=request.correlation_id,
                    status="error",
                    error_message=f"Tool not found: {request.tool_flat_name}",
                    started_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc),
                    latency_ms=0
                )

            # 1. Normalize and Validate Input
            try:
                request.arguments = normalize_arguments(spec, request.arguments, request.scope)
            except InputValidationError as e:
                return ToolInvocationResult(
                    correlation_id=request.correlation_id,
                    status="error",
                    error_message=e.message,
                    started_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc),
                    latency_ms=0
                )

            # 2. Policy Gate & Dispatch (PolicyGate calls dispatcher if allowed)
            async def _dispatch_step(db_session, req, tool_spec, sanitized_args):
                started_at = datetime.now(timezone.utc)
                raw_output = None
                error_msg = None
                
                try:
                    if tool_spec.execution_backend == "native":
                        raw_output = await self.native_dispatcher.dispatch(db_session, req, tool_spec, sanitized_args)
                    else:
                        # Extension provider dispatch (future phase)
                        raw_output = {"error": f"Unsupported backend {tool_spec.execution_backend}"}
                except Exception as e:
                    logger.exception(f"Tool execution failed: {e}")
                    error_msg = str(e)
                
                finished_at = datetime.now(timezone.utc)
                
                if error_msg:
                    return ToolInvocationResult(
                        correlation_id=req.correlation_id,
                        status="error",
                        error_message=error_msg,
                        started_at=started_at,
                        finished_at=finished_at,
                        latency_ms=int((finished_at - started_at).total_seconds() * 1000)
                    )
                
                # 3. Format Output
                return format_output(tool_spec, raw_output, req.correlation_id, started_at, finished_at)

            # PolicyGate is sync but returns awaitable if next_step is async
            result = self.policy_gate.execute_if_allowed(db, request, _dispatch_step)
            if asyncio.iscoroutine(result):
                return await result
            return result

        except Exception as e:
            logger.exception(f"Unhandled tool invocation error: {e}")
            now = datetime.now(timezone.utc)
            return ToolInvocationResult(
                correlation_id=request.correlation_id,
                status="error",
                error_message="Internal error during tool invocation",
                started_at=now,
                finished_at=now,
                latency_ms=0
            )

async def invoke_tool_legacy(
    spec: ToolSpec,
    db: Session,
    workspace_id: int,
    user_id: int,
    arguments: Dict[str, Any]
) -> Any:
    """
    Bridge function preserving the exact signature of legacy `execute_tool_spec`.
    Translates legacy kwargs into a ToolInvocationRequest and unboxes the result.
    """
    scope = ExecutionScope(
        workspace_id=workspace_id,
        company_id=workspace_id, # Fallback, as legacy only had workspace_id
        principal_user_id=user_id,
        principal_member_id=user_id, # Fallback
        principal_role="owner", # Elevated assumption for legacy chat bypass
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=()
    )
    
    req = ToolInvocationRequest(
        scope=scope,
        tool_flat_name=spec.flat_name,
        arguments=arguments,
        source="legacy_chat"
    )
    
    service = ToolInvocationService()
    result = await service.invoke(db, req)
    
    if result.status == "success":
        return result.output
    elif result.status == "error":
        raise ToolInvocationError(result.error_message or "Unknown error")
    elif result.status == "approval_required":
        return {"approval_id": result.approval_id, "status": "pending_approval"}
    else:
        return {"error": result.error_message, "status": result.status}
