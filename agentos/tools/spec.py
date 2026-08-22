from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Literal, Optional, Union
import jsonschema
from pydantic import BaseModel, ConfigDict, Field

from agentos.core.policy import (
    PERMISSION_CLASS_RISK_MAPPING,
    PermissionClass,
    ToolPermission,
    ToolRiskLevel,
)


class ToolValidationError(Exception):
    """Raised when tool input or output fails schema validation."""

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ToolExecutionTimeoutError(Exception):
    """Raised when tool execution exceeds its timeout."""

    def __init__(self, tool_name: str, timeout_seconds: int) -> None:
        super().__init__(f"Tool '{tool_name}' timed out after {timeout_seconds}s")
        self.tool_name = tool_name
        self.timeout_seconds = timeout_seconds


class ToolSpecV2(BaseModel):
    """Tool specification V2 (§10.3) with full metadata, typing, and validation schemas."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str  # "<domain>.<resource>.<action>"
    version: str = "1.0.0"
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    handler: Callable[..., Any]
    permission_class: Optional[str] = None  # Backward compatibility
    risk_level: ToolRiskLevel = ToolRiskLevel.LOW
    tool_permission: ToolPermission = ToolPermission.READ_ONLY
    write_scope: Literal["workspace", "company", "none"] = "none"
    idempotent: bool = True
    reversible: bool = True
    approval_policy: Literal["always", "conditional", "never"] = "conditional"
    audit_policy: Literal["full", "minimal"] = "full"
    timeout_seconds: Union[int, float] = 15
    tags: list[str] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        # Infer risk_level and tool_permission from legacy permission_class if not set
        if self.permission_class:
            try:
                p_enum = PermissionClass(self.permission_class)
                if p_enum in PERMISSION_CLASS_RISK_MAPPING:
                    mapped_risk, mapped_perm = PERMISSION_CLASS_RISK_MAPPING[p_enum]
                    if self.risk_level == ToolRiskLevel.LOW:
                        self.risk_level = ToolRiskLevel(mapped_risk)
                    if self.tool_permission == ToolPermission.READ_ONLY:
                        self.tool_permission = ToolPermission(mapped_perm)
            except Exception:
                pass


def validate_tool_input(schema: dict[str, Any], arguments: dict[str, Any], tool_name: str = "") -> None:
    """Validate tool input arguments against its JSON schema."""
    if not schema:
        return
    try:
        jsonschema.validate(instance=arguments, schema=schema)
    except jsonschema.ValidationError as err:
        tool_prefix = f"for tool '{tool_name}' " if tool_name else ""
        raise ToolValidationError(
            f"Input schema validation failed {tool_prefix}: {err.message}",
            details=err.schema_path,
        ) from err


def validate_tool_output(schema: dict[str, Any], result: Any, tool_name: str = "") -> None:
    """Validate tool execution output against its JSON schema."""
    if not schema:
        return
    try:
        jsonschema.validate(instance=result, schema=schema)
    except jsonschema.ValidationError as err:
        tool_prefix = f"for tool '{tool_name}' " if tool_name else ""
        raise ToolValidationError(
            f"Output schema validation failed {tool_prefix}: {err.message}",
            details=err.schema_path,
        ) from err


ToolSpecV2.model_rebuild()
