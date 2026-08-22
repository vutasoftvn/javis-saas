"""Safe, unified tool execution and parameter injection for chat and agent runtime.

Guarantees tenant isolation by ignoring model-supplied identifiers (`workspace_id`,
`user_id`, etc.) and injecting strictly server-derived parameters.
"""

from __future__ import annotations

import inspect
import json
import logging
from typing import TYPE_CHECKING, Any, Optional, Union

from sqlalchemy.orm import Session

from cosa_core.tools.registry import ToolSpec

if TYPE_CHECKING:
    from cosa_core.governance.kernel import GovernanceDecision

logger = logging.getLogger(__name__)

# Server-derived parameters that must never be trusted from model input
INJECTED_PARAMS = (
    "db",
    "workspace_id",
    "user_id",
    "chat_session_id",
    "agent_key",
    "agent_run_id",
)

ID_PARAM_SUFFIXES = ("_id", "_no")


def tool_needs_param(spec: ToolSpec, param: str) -> bool:
    """Check if the tool's callable signature accepts the specified parameter."""
    try:
        return param in inspect.signature(spec.callable).parameters
    except (TypeError, ValueError):
        return False


def coerce_tool_args(spec: ToolSpec, args: dict[str, Any]) -> dict[str, Any]:
    """Coerce model arguments according to callable signature, stripping unrecognized
    or injected parameter names.
    """
    try:
        parameters = inspect.signature(spec.callable).parameters
    except (TypeError, ValueError):
        return args

    # Connector-backed tools register a **kwargs marker callable (the real signature
    # lives in the extension's JSON schema, validated later by normalize_arguments) -
    # filtering by exact parameter name would strip every argument.
    accepts_any_kwarg = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters.values()
    )

    coerced: dict[str, Any] = {}
    for name, value in args.items():
        if name in INJECTED_PARAMS:
            continue
        if not accepts_any_kwarg and name not in parameters:
            # Model generated extra parameters the callable doesn't accept
            continue
        if value is not None and name.endswith(ID_PARAM_SUFFIXES):
            try:
                value = int(value)
            except (TypeError, ValueError):
                return {"__error__": f"Tham số {name} phải là một id hợp lệ, nhận được {value!r}"}
        coerced[name] = value
    return coerced


async def execute_tool_spec(
    spec: ToolSpec,
    db: Session,
    workspace_id: int,
    user_id: Optional[int] = None,
    chat_session_id: Optional[int] = None,
    agent_key: Optional[str] = None,
    agent_run_id: Optional[int] = None,
    arguments: Union[str, dict[str, Any], None] = None,
    governance_decision: Optional[GovernanceDecision] = None,
) -> Any:
    """Execute a ToolSpec safely, injecting runtime parameters."""
    # COSA-CORE-BOUNDARY-EXCEPTION: workforce.tools.invocation.service (Batch 2)
    # Lazy import to avoid circular dependency — workforce.tools.invocation not yet
    # extracted to cosa_core (scheduled for Batch 2). See docs/architecture/2026-08-22-cosa-core-extraction-plan.md
    from workforce.tools.invocation.service import invoke_tool_via_spec
    return await invoke_tool_via_spec(
        spec=spec,
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        arguments=arguments,
        chat_session_id=chat_session_id,
        governance_decision=governance_decision,
    )
