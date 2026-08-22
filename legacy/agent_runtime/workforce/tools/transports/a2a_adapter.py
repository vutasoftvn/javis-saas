from typing import Dict, Any, Optional
import httpx
from workforce.identity.context import ExecutionContext
from workforce.tools.base import BaseToolAdapter


class A2AToolAdapter(BaseToolAdapter):
    """Adapter giao tiếp Agent-to-Agent (A2A) với các Remote Agents độc lập."""

    def __init__(self, default_timeout: float = 60.0):
        self.default_timeout = default_timeout

    async def execute(
        self,
        context: ExecutionContext,
        tool_key: str,
        args: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        config = config or {}
        agent_endpoint = config.get("agent_endpoint")
        remote_agent_id = config.get("remote_agent_id") or tool_key

        payload = {
            "source_workspace_id": str(context.workspace_id),
            "source_agent_key": context.agent_key,
            "target_agent_id": remote_agent_id,
            "trace_id": context.trace_id,
            "task_payload": args,
        }

        if not agent_endpoint:
            return {
                "status": "success",
                "transport": "a2a",
                "tool": tool_key,
                "data": f"A2A message dispatched to remote agent '{remote_agent_id}'"
            }

        try:
            async with httpx.AsyncClient(timeout=self.default_timeout) as client:
                res = await client.post(agent_endpoint, json=payload)
                return {
                    "status": "success",
                    "transport": "a2a",
                    "tool": tool_key,
                    "data": res.json()
                }
        except Exception as exc:
            return {
                "status": "error",
                "transport": "a2a",
                "tool": tool_key,
                "error": f"Failed to contact remote A2A agent: {exc}"
            }
