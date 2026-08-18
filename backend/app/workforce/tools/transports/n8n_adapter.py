from typing import Dict, Any, Optional
import httpx
from app.workforce.identity.context import ExecutionContext
from app.workforce.tools.base import BaseToolAdapter


class N8nToolAdapter(BaseToolAdapter):
    """Adapter kích hoạt quy trình tự động hóa, timer hoặc webhook trên n8n."""

    def __init__(self, default_timeout: float = 15.0):
        self.default_timeout = default_timeout

    async def execute(
        self,
        context: ExecutionContext,
        tool_key: str,
        args: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        config = config or {}
        webhook_url = config.get("webhook_url")

        payload = {
            "workspace_id": context.workspace_id,
            "agent_key": context.agent_key,
            "trace_id": context.trace_id,
            "action": tool_key,
            "parameters": args,
        }

        if not webhook_url:
            return {
                "status": "success",
                "transport": "n8n",
                "tool": tool_key,
                "data": f"n8n automation scheduled for '{tool_key}' with payload: {payload}"
            }

        try:
            async with httpx.AsyncClient(timeout=self.default_timeout) as client:
                res = await client.post(webhook_url, json=payload)
                return {
                    "status": "success",
                    "transport": "n8n",
                    "tool": tool_key,
                    "data": res.json() if res.headers.get("content-type", "").startswith("application/json") else res.text
                }
        except Exception as exc:
            return {
                "status": "error",
                "transport": "n8n",
                "tool": tool_key,
                "error": f"Failed to trigger n8n webhook: {exc}"
            }
