from sqlalchemy.orm import Session
from typing import Any, Dict
from dataclasses import replace as dataclass_replace
from datetime import datetime, timezone
import asyncio
import logging

from cosa_core.tools.registry import ToolSpec
from cosa_core.tools.invocation.contracts import ToolInvocationRequest, ToolInvocationResult, ToolInvocationError
from cosa_core.tools.invocation.input_validation import normalize_arguments, InputValidationError
from cosa_core.tools.invocation.policy_gate import PolicyGate
from cosa_core.tools.invocation.dispatchers import NativeDispatcher
from cosa_core.tools.invocation.output_safety import format_output
from cosa_core.runtime.execution_scope import ExecutionScope
from cosa_core.governance.kernel import GovernanceDecision
from cosa_core.governance.policy_engine import PolicyAction
from workforce.extensions.capability_bridge import CapabilityBridge
from workforce.extensions.contracts import ProviderProtocolError, ProviderUnavailableError
from workforce.extensions.eligibility import resolve_eligible_capabilities
from workforce.extensions.mcp_provider import MCPProvider
from workforce.extensions.registry import ExtensionRegistry
from workforce.extensions.seams import ProviderResult
from workforce.extensions.tool_registration import (
    extension_tool_spec,
    tool_specs_semantically_identical,
)

logger = logging.getLogger(__name__)

class ToolInvocationService:
    def __init__(self):
        self.policy_gate = PolicyGate()
        self.native_dispatcher = NativeDispatcher()

    async def invoke(self, db: Session, request: ToolInvocationRequest) -> ToolInvocationResult:
        try:
            # We need the spec first.
            # get_tool_by_flat_name is used in PolicyGate, but we also need it for input validation
            from cosa_core.tools.registry import get_tool_by_flat_name
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
            async def _dispatch_step(
                db_session,
                req,
                tool_spec,
                sanitized_args,
                governance_decision=None,
            ):
                started_at = datetime.now(timezone.utc)
                raw_output = None
                error_msg = None
                
                try:
                    if tool_spec.execution_backend == "native":
                        raw_output = await self.native_dispatcher.dispatch(db_session, req, tool_spec, sanitized_args)
                    elif tool_spec.execution_backend == "connector":
                        eligible = next(
                            (
                                capability
                                for capability in resolve_eligible_capabilities(
                                    db_session, req.scope
                                )
                                if capability.eligible
                                and capability.extension_id == tool_spec.backend_id
                                and capability.name == tool_spec.name
                            ),
                            None,
                        )
                        if eligible is None:
                            raise LookupError(
                                f"Connector capability is not eligible: {tool_spec.qualified_name}"
                            )

                        extension_registry = ExtensionRegistry()
                        capability = extension_registry.get_capability(
                            db_session,
                            req.scope.workspace_id,
                            eligible.capability_id,
                        )
                        if capability is None:
                            raise LookupError(
                                f"Connector capability is unavailable: {tool_spec.qualified_name}"
                            )

                        registration = extension_registry.get(
                            db_session,
                            req.scope.workspace_id,
                            eligible.extension_id,
                        )
                        if registration is None or not tool_specs_semantically_identical(
                            tool_spec,
                            extension_tool_spec(
                                eligible,
                                capability,
                                registration.manifest_jsonb,
                            ),
                        ):
                            raise LookupError(
                                f"Connector capability does not match governed ToolSpec: {tool_spec.qualified_name}"
                            )

                        # A pre-evaluated decision's sanitized_args may predate
                        # normalization (GovernanceKernel.sanitized_args is the raw
                        # args it was asked to evaluate, not a sanitized copy) - always
                        # re-strip reserved connector context right before dispatch
                        # rather than trusting whatever the caller attached.
                        sanitized_args = normalize_arguments(tool_spec, sanitized_args, req.scope)

                        decision = governance_decision or GovernanceDecision(
                            allowed=True,
                            action=PolicyAction.ALLOW,
                            reason="Authorized by ToolInvocationService policy gate",
                            tool_spec=tool_spec,
                            sanitized_args=sanitized_args,
                        )
                        decision = dataclass_replace(decision, sanitized_args=sanitized_args)
                        provider_result = await CapabilityBridge().invoke(
                            db_session,
                            req.scope,
                            req,
                            None,
                            capability,
                            MCPProvider(),
                            decision,
                        )
                        raw_output = (
                            provider_result.result
                            if isinstance(provider_result, ProviderResult)
                            and provider_result.status == "success"
                            else provider_result
                        )
                    else:
                        raw_output = {"error": f"Unsupported backend {tool_spec.execution_backend}"}
                except (ProviderProtocolError, ProviderUnavailableError) as e:
                    # Never trust a connector provider's exception text verbatim - it
                    # can embed the upstream endpoint URL or credentials (see
                    # mcp_provider.py's own redaction for the common case; this is the
                    # backstop for any other ConnectorProvider implementation).
                    logger.exception(f"Connector provider request failed: {e}")
                    error_msg = "Connector provider request failed"
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

            if request.governance_decision is not None:
                decision = request.governance_decision
                if decision.action != PolicyAction.ALLOW:
                    return _blocked_result(request, decision)
                return await _dispatch_step(
                    db,
                    request,
                    decision.tool_spec or spec,
                    (
                        decision.sanitized_args
                        if decision.sanitized_args is not None
                        else request.arguments
                    ),
                    decision,
                )

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


def _blocked_result(
    request: ToolInvocationRequest, decision: GovernanceDecision
) -> ToolInvocationResult:
    now = datetime.now(timezone.utc)
    approval_required = decision.action == PolicyAction.REQUIRE_APPROVAL
    return ToolInvocationResult(
        correlation_id=request.correlation_id,
        status="approval_required" if approval_required else "denied",
        error_message=decision.reason,
        approval_id=(
            str(decision.approval.id)
            if approval_required and decision.approval
            else None
        ),
        started_at=now,
        finished_at=now,
        latency_ms=0,
    )

async def invoke_tool_via_spec(
    spec: ToolSpec,
    db: Session,
    workspace_id: int,
    user_id: int,
    arguments: Dict[str, Any],
    chat_session_id: int | None = None,
    governance_decision: GovernanceDecision | None = None,
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
        source="legacy_chat",
        governance_decision=governance_decision,
        chat_session_id=chat_session_id,
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
