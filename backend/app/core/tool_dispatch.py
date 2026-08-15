"""Safe, unified tool execution and parameter injection for chat and agent runtime.

Guarantees tenant isolation by ignoring model-supplied identifiers (`workspace_id`,
`user_id`, etc.) and injecting strictly server-derived parameters.
"""

import inspect
import json
import logging
from typing import Any, Optional, Union

from sqlalchemy.orm import Session

from app.core.tool_registry import ToolSpec

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

    coerced: dict[str, Any] = {}
    for name, value in args.items():
        if name not in parameters or name in INJECTED_PARAMS:
            # Model generated extra parameters or attempted to pass injected params like workspace_id
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
) -> Any:
    """Execute a ToolSpec safely, injecting runtime parameters."""
    if isinstance(arguments, str):
        try:
            raw_args = json.loads(arguments or "{}")
            if not isinstance(raw_args, dict):
                raw_args = {}
        except json.JSONDecodeError:
            return {"error": "Tham số tool không phải JSON hợp lệ"}
    elif isinstance(arguments, dict):
        raw_args = arguments
    else:
        raw_args = {}

    kwargs = coerce_tool_args(spec, raw_args)
    if "__error__" in kwargs:
        return {"error": kwargs["__error__"]}

    injected = {
        "db": db,
        "workspace_id": workspace_id,
        "user_id": user_id,
        "chat_session_id": chat_session_id,
        "agent_key": agent_key,
        "agent_run_id": agent_run_id,
    }

    for param, value in injected.items():
        if tool_needs_param(spec, param):
            if value is None and param != "db":
                return {"error": f"Không đủ quyền hoặc thiếu thông tin ngữ cảnh để dùng tool {spec.qualified_name} (thiếu {param})"}
            kwargs[param] = value

    try:
        result = spec.callable(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result
    except TypeError as exc:
        logger.info("Tool %s bị gọi sai tham số: %s", spec.qualified_name, exc)
        return {"error": f"Gọi tool thiếu tham số hoặc sai định dạng: {exc}"}
    except Exception as exc:
        logger.exception("Tool %s thất bại: %s", spec.qualified_name, exc)
        db.rollback()
        return {"error": f"Tra cứu dữ liệu thất bại: {exc}"}
