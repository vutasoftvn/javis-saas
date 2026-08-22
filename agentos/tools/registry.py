from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Optional


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: Callable[[dict], Awaitable[dict]]
    permission_class: Optional[str] = None


class ToolNotFoundError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Tool not registered: {name}")
        self.name = name


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError:
            raise ToolNotFoundError(name) from None

    def names(self) -> list[str]:
        return sorted(self._tools)

    def all_specs(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def list_tools(self) -> list[ToolSpec]:
        return self.all_specs()

    async def invoke(self, name: str, arguments: dict) -> dict:
        spec = self.get(name)
        return await spec.handler(arguments)

    def register_cluster_tools(self, encore_client: Optional[Any] = None) -> None:
        """Đăng ký toàn bộ tools của 4 Business Service Clusters vào registry."""
        from agentos.tools.clusters.operations_tools import get_operations_tools
        from agentos.tools.clusters.commercial_tools import get_commercial_tools
        from agentos.tools.clusters.finance_tools import get_finance_tools
        from agentos.tools.clusters.identity_tools import get_identity_tools

        for tool in get_operations_tools(encore_client):
            self.register(tool)
        for tool in get_commercial_tools(encore_client):
            self.register(tool)
        for tool in get_finance_tools(encore_client):
            self.register(tool)
        for tool in get_identity_tools(encore_client):
            self.register(tool)
