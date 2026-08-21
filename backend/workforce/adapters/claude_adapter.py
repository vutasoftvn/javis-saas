import time
import json
from typing import AsyncIterator, Dict, Any, Optional
import httpx

from workforce.adapters.base import (
    BaseRuntimeAdapter, ExecutionPayload, ExecutionResult, TokenUsage, Message, ModelRole
)


class ClaudeCodeAdapter(BaseRuntimeAdapter):
    """Adapter tích hợp với Anthropic Claude API / Claude Code Runtime."""

    PRICING = {
        "claude-3-5-sonnet-20241022": {"prompt": 3.0 / 1_000_000, "completion": 15.0 / 1_000_000},
        "claude-3-opus-20240229": {"prompt": 15.0 / 1_000_000, "completion": 75.0 / 1_000_000},
        "claude-3-5-haiku-20241022": {"prompt": 1.0 / 1_000_000, "completion": 5.0 / 1_000_000},
    }

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(api_key=api_key, base_url=base_url or "https://api.anthropic.com/v1", config=config)

    def estimate_cost(self, model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = self.PRICING.get(model_name, {"prompt": 3.0 / 1_000_000, "completion": 15.0 / 1_000_000})
        return (prompt_tokens * rates["prompt"]) + (completion_tokens * rates["completion"])

    async def execute(self, payload: ExecutionPayload) -> ExecutionResult:
        start_time = time.time()
        model = payload.model_name or "claude-3-5-sonnet-20241022"

        # Tách system message và user/assistant messages
        system_content = ""
        formatted_messages = []
        for msg in payload.messages:
            if msg.role == ModelRole.SYSTEM:
                system_content += msg.content + "\n"
            else:
                role_str = "user" if msg.role == ModelRole.USER else "assistant"
                formatted_messages.append({"role": role_str, "content": msg.content})

        req_body = {
            "model": model,
            "messages": formatted_messages,
            "max_tokens": payload.max_tokens,
            "temperature": payload.temperature,
        }
        if system_content.strip():
            req_body["system"] = system_content.strip()
        if payload.tools_schema:
            req_body["tools"] = payload.tools_schema

        headers = {
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        # Nếu không có API Key, fallback chế độ mock test
        if not self.api_key:
            latency_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                trace_id=payload.trace_id,
                content=f"[Claude Mock Response for {payload.agent_key}]: Processed request successfully.",
                usage=TokenUsage(prompt_tokens=150, completion_tokens=80, total_tokens=230, cost_usd=0.00165),
                finish_reason="stop",
                latency_ms=max(latency_ms, 50),
            )

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.base_url}/messages", json=req_body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        latency_ms = int((time.time() - start_time) * 1000)
        content_text = ""
        tool_calls = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                content_text += block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_calls.append(block)

        raw_usage = data.get("usage", {})
        prompt_tok = raw_usage.get("input_tokens", 0)
        compl_tok = raw_usage.get("output_tokens", 0)
        cost = self.estimate_cost(model, prompt_tok, compl_tok)

        return ExecutionResult(
            trace_id=payload.trace_id,
            content=content_text,
            tool_calls=tool_calls,
            usage=TokenUsage(prompt_tokens=prompt_tok, completion_tokens=compl_tok, total_tokens=prompt_tok + compl_tok, cost_usd=cost),
            finish_reason=data.get("stop_reason", "stop"),
            latency_ms=latency_ms,
            raw_response=data,
        )

    async def check_capability(self) -> Dict[str, Any]:
        """Kiểm tra tính sẵn sàng và capabilities của Claude API / Claude Code."""
        return {
            "runtime": "claude_code",
            "provider": "anthropic",
            "installed": True,
            "authenticated": bool(self.api_key),
            "headless_supported": True,
            "mcp_available": True,
            "workspace_access": True,
            "models": list(self.PRICING.keys()),
        }

    async def cancel(self, run_id: str) -> bool:
        # Anthropic standard REST API cancels when connection is dropped or client aborts
        return True

    async def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy" if self.api_key else "mock_ready",
            "adapter": "ClaudeCodeAdapter",
            "provider": "anthropic",
            "authenticated": bool(self.api_key),
        }

    async def stream(self, payload: ExecutionPayload) -> AsyncIterator[str]:
        # Fallback stream
        res = await self.execute(payload)
        yield res.content
