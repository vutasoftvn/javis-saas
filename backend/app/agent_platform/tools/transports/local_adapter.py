from typing import Dict, Any, Optional, Callable, Awaitable
import inspect
from app.agent_platform.identity.context import ExecutionContext
from app.agent_platform.tools.base import BaseToolAdapter


class LocalToolAdapter(BaseToolAdapter):
    """Adapter thực thi các công cụ viết trực tiếp bằng Python nội bộ trong hệ thống."""

    def __init__(self):
        self._registry: Dict[str, Callable[..., Any]] = {}

    def register(self, tool_key: str, func: Callable[..., Any]):
        self._registry[tool_key] = func

    async def execute(
        self,
        context: ExecutionContext,
        tool_key: str,
        args: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        handler = self._registry.get(tool_key)
        if not handler:
            return {
                "status": "success",
                "transport": "local",
                "tool": tool_key,
                "data": f"Local mock execution for '{tool_key}' with args: {args}"
            }

        if inspect.iscoroutinefunction(handler):
            res = await handler(context, args)
        else:
            res = handler(context, args)
            if inspect.isawaitable(res):
                res = await res

        return {
            "status": "success",
            "transport": "local",
            "tool": tool_key,
            "data": res
        }
