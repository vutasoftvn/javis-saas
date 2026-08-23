from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Union

from agentos.core.policy import (
    PERMISSION_CLASS_RISK_MAPPING,
    PermissionClass,
    ToolPermission,
    ToolRiskLevel,
)
from agentos.tools.spec import (
    ToolExecutionTimeoutError,
    ToolSpecV2,
    ToolValidationError,
    validate_tool_input,
    validate_tool_output,
)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: Callable[[dict], Awaitable[dict]]
    permission_class: Optional[str] = None
    risk_level: Optional[ToolRiskLevel] = None
    tool_permission: Optional[ToolPermission] = None
    input_schema: Optional[dict[str, Any]] = None
    output_schema: Optional[dict[str, Any]] = None
    timeout_seconds: int = 15
    approval_policy: str = "conditional"
    audit_policy: str = "full"

    def __post_init__(self) -> None:
        r_level = self.risk_level
        t_perm = self.tool_permission
        if self.permission_class and (r_level is None or t_perm is None):
            try:
                p_enum = PermissionClass(self.permission_class)
                if p_enum in PERMISSION_CLASS_RISK_MAPPING:
                    mapped_risk, mapped_perm = PERMISSION_CLASS_RISK_MAPPING[p_enum]
                    if r_level is None:
                        r_level = ToolRiskLevel(mapped_risk)
                    if t_perm is None:
                        t_perm = ToolPermission(mapped_perm)
            except Exception:
                pass
        if r_level is None:
            r_level = ToolRiskLevel.LOW
        if t_perm is None:
            t_perm = ToolPermission.READ_ONLY
        object.__setattr__(self, "risk_level", r_level)
        object.__setattr__(self, "tool_permission", t_perm)


class ToolNotFoundError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Tool not registered: {name}")
        self.name = name


# Canonical to legacy shorthand alias generator helper
def _infer_legacy_alias(canonical_name: str) -> Optional[str]:
    """operations.task.create -> task_create, commercial.lead.create -> lead_create"""
    parts = canonical_name.split(".")
    if len(parts) == 3:
        domain, resource, action = parts
        return f"{resource}_{action}"
    return None


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Union[ToolSpec, ToolSpecV2]] = {}
        self._aliases: dict[str, str] = {}

    def register(self, spec: Union[ToolSpec, ToolSpecV2]) -> None:
        self._tools[spec.name] = spec
        # Automatically register alias if canonical name follows <domain>.<resource>.<action>
        legacy_alias = _infer_legacy_alias(spec.name)
        if legacy_alias and legacy_alias not in self._tools:
            self._aliases[legacy_alias] = spec.name

    def register_alias(self, alias: str, target_name: str) -> None:
        self._aliases[alias] = target_name

    def get(self, name: str) -> Union[ToolSpec, ToolSpecV2]:
        if name in self._tools:
            return self._tools[name]
        if name in self._aliases and self._aliases[name] in self._tools:
            return self._tools[self._aliases[name]]
        raise ToolNotFoundError(name)

    def names(self) -> list[str]:
        return sorted(set(self._tools.keys()) | set(self._aliases.keys()))

    def all_specs(self) -> list[Union[ToolSpec, ToolSpecV2]]:
        return list(self._tools.values())

    def list_tools(self) -> list[Union[ToolSpec, ToolSpecV2]]:
        return self.all_specs()

    async def invoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        spec = self.get(name)
        input_schema = getattr(spec, "input_schema", None) or {}
        validate_tool_input(input_schema, arguments, tool_name=spec.name)

        timeout = getattr(spec, "timeout_seconds", 15)
        try:
            handler_result = spec.handler(arguments)
            if asyncio.iscoroutine(handler_result) or hasattr(handler_result, "__await__"):
                result = await asyncio.wait_for(handler_result, timeout=timeout)
            else:
                result = handler_result
        except asyncio.TimeoutError:
            raise ToolExecutionTimeoutError(spec.name, timeout)

        output_schema = getattr(spec, "output_schema", None) or {}
        validate_tool_output(output_schema, result, tool_name=spec.name)
        return result

    def register_cluster_tools(self, encore_client: Optional[Any] = None) -> None:
        """Đăng ký toàn bộ tools của Business Service Clusters (operations, strategy, commercial, finance, identity) vào registry."""
        from agentos.tools.clusters.operations_tools import get_operations_tools
        from agentos.tools.clusters.strategy_tools import get_strategy_tools
        from agentos.tools.clusters.commercial_tools import get_commercial_tools
        from agentos.tools.clusters.finance_tools import get_finance_tools
        from agentos.tools.clusters.identity_tools import get_identity_tools

        for tool in get_operations_tools(encore_client):
            self.register(tool)
        for tool in get_strategy_tools(encore_client):
            self.register(tool)
        for tool in get_commercial_tools(encore_client):
            self.register(tool)
        for tool in get_finance_tools(encore_client):
            self.register(tool)
        for tool in get_identity_tools(encore_client):
            self.register(tool)
