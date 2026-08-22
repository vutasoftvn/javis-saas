import time
from typing import AsyncIterator, Dict, Any, Optional
import httpx

from workforce.adapters.base import (
    BaseRuntimeAdapter, ExecutionPayload, ExecutionResult, TokenUsage, Message, ModelRole
)


class DeepSeekAdapter(BaseRuntimeAdapter):
    """Adapter tích hợp với DeepSeek API (DeepSeek-V3 / DeepSeek-R1 reasoning)."""

    PRICING = {
        "deepseek-chat": {"prompt": 0.14 / 1_000_000, "completion": 0.28 / 1_000_000},
        "deepseek-reasoner": {"prompt": 0.55 / 1_000_000, "completion": 2.19 / 1_000_000},
    }

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            api_key=api_key,
            base_url=base_url or "https://api.deepseek.com/v1",
            config=config
        )

    def estimate_cost(self, model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = self.PRICING.get(model_name, {"prompt": 0.14 / 1_000_000, "completion": 0.28 / 1_000_000})
        return (prompt_tokens * rates["prompt"]) + (completion_tokens * rates["completion"])

    async def execute(self, payload: ExecutionPayload) -> ExecutionResult:
        start_time = time.time()
        model = payload.model_name or "deepseek-chat"

        # Nếu không có API Key, fallback chế độ mock test
        if not self.api_key:
            latency_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                trace_id=payload.trace_id,
                content=f"[DeepSeek Mock Response for {payload.agent_key}]: Chain-of-thought analysis complete. Work product ready.",
                usage=TokenUsage(prompt_tokens=210, completion_tokens=120, total_tokens=330, cost_usd=0.000063),
                finish_reason="stop",
                latency_ms=max(latency_ms, 60),
            )

        messages = []
        for msg in payload.messages:
            role_str = "user"
            if msg.role == ModelRole.SYSTEM:
                role_str = "system"
            elif msg.role == ModelRole.ASSISTANT:
                role_str = "assistant"
            messages.append({"role": role_str, "content": msg.content})

        req_body: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": payload.temperature,
            "max_tokens": payload.max_tokens,
        }
        if payload.tools_schema:
            req_body["tools"] = payload.tools_schema

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", json=req_body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        latency_ms = int((time.time() - start_time) * 1000)
        choices = data.get("choices", [])
        content_text = ""
        tool_calls = []
        finish_reason = "stop"

        if choices:
            choice = choices[0]
            finish_reason = choice.get("finish_reason", "stop")
            msg_data = choice.get("message", {})
            content_text = msg_data.get("content", "")
            tool_calls = msg_data.get("tool_calls", [])

        usage_data = data.get("usage", {})
        prompt_tok = usage_data.get("prompt_tokens", 0)
        compl_tok = usage_data.get("completion_tokens", 0)
        cost = self.estimate_cost(model, prompt_tok, compl_tok)

        return ExecutionResult(
            trace_id=payload.trace_id,
            content=content_text,
            tool_calls=tool_calls,
            usage=TokenUsage(prompt_tokens=prompt_tok, completion_tokens=compl_tok, total_tokens=prompt_tok + compl_tok, cost_usd=cost),
            finish_reason=finish_reason,
            latency_ms=latency_ms,
            raw_response=data,
        )

    async def check_capability(self) -> Dict[str, Any]:
        """Kiểm tra tính sẵn sàng và capabilities của DeepSeek API."""
        return {
            "runtime": "deepseek",
            "provider": "deepseek",
            "installed": True,
            "authenticated": bool(self.api_key),
            "headless_supported": True,
            "mcp_available": False,
            "workspace_access": False,
            "models": list(self.PRICING.keys()),
        }

    async def cancel(self, run_id: str) -> bool:
        return True

    async def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy" if self.api_key else "mock_ready",
            "adapter": "DeepSeekAdapter",
            "provider": "deepseek",
            "authenticated": bool(self.api_key),
        }

    async def stream(self, payload: ExecutionPayload) -> AsyncIterator[str]:
        res = await self.execute(payload)
        yield res.content
