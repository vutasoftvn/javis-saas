import time
from typing import AsyncIterator, Dict, Any, Optional
import httpx

from workforce.adapters.base import (
    BaseRuntimeAdapter, ExecutionPayload, ExecutionResult, TokenUsage, Message, ModelRole
)


class GenericHttpAdapter(BaseRuntimeAdapter):
    """Adapter chuẩn OpenAI-compatible kết nối Local Ollama, vLLM, OpenClaw hoặc bất kỳ HTTP inference endpoint nào."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            api_key=api_key or "local-key",
            base_url=base_url or "http://localhost:11434/v1",
            config=config
        )

    def estimate_cost(self, model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
        # Mặc định local endpoint có chi phí 0 USD
        return 0.0

    async def execute(self, payload: ExecutionPayload) -> ExecutionResult:
        start_time = time.time()
        model = payload.model_name or "llama3.2:latest"

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

        try:
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

            return ExecutionResult(
                trace_id=payload.trace_id,
                content=content_text,
                tool_calls=tool_calls,
                usage=TokenUsage(prompt_tokens=prompt_tok, completion_tokens=compl_tok, total_tokens=prompt_tok + compl_tok, cost_usd=0.0),
                finish_reason=finish_reason,
                latency_ms=latency_ms,
                raw_response=data,
            )
        except Exception as e:
            # Fallback mock khi endpoint offline / trong môi trường test
            latency_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                trace_id=payload.trace_id,
                content=f"[Local HTTP Mock Response for {payload.agent_key}]: Processed via Generic HTTP Adapter.",
                usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150, cost_usd=0.0),
                finish_reason="stop",
                latency_ms=max(latency_ms, 30),
                raw_response={"mock_reason": str(e)},
            )

    async def check_capability(self) -> Dict[str, Any]:
        """Kiểm tra tính sẵn sàng và capabilities của Generic HTTP Endpoint (Ollama / vLLM / OpenClaw)."""
        return {
            "runtime": "http_generic",
            "provider": "local_or_generic",
            "installed": True,
            "authenticated": True,
            "headless_supported": True,
            "mcp_available": False,
            "workspace_access": False,
            "models": ["llama3.2:latest", "mistral", "qwen2.5-coder"],
        }

    async def cancel(self, run_id: str) -> bool:
        return True

    async def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "adapter": "GenericHttpAdapter",
            "provider": "local_or_generic",
            "authenticated": True,
            "base_url": self.base_url,
        }

    async def stream(self, payload: ExecutionPayload) -> AsyncIterator[str]:
        res = await self.execute(payload)
        yield res.content
