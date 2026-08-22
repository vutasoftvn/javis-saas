import time
from typing import AsyncIterator, Dict, Any, Optional
import httpx

from workforce.adapters.base import (
    BaseRuntimeAdapter, ExecutionPayload, ExecutionResult, TokenUsage, Message, ModelRole
)


class GeminiAdapter(BaseRuntimeAdapter):
    """Adapter tích hợp với Google Gemini API (2.0 Flash / 1.5 Pro) và ADK 2.0."""

    PRICING = {
        "gemini-2.0-flash": {"prompt": 0.10 / 1_000_000, "completion": 0.40 / 1_000_000},
        "gemini-1.5-pro": {"prompt": 1.25 / 1_000_000, "completion": 5.0 / 1_000_000},
        "gemini-1.5-flash": {"prompt": 0.075 / 1_000_000, "completion": 0.30 / 1_000_000},
    }

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            api_key=api_key,
            base_url=base_url or "https://generativelanguage.googleapis.com/v1beta",
            config=config
        )

    def estimate_cost(self, model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = self.PRICING.get(model_name, {"prompt": 0.10 / 1_000_000, "completion": 0.40 / 1_000_000})
        return (prompt_tokens * rates["prompt"]) + (completion_tokens * rates["completion"])

    async def execute(self, payload: ExecutionPayload) -> ExecutionResult:
        start_time = time.time()
        model = payload.model_name or "gemini-2.0-flash"

        # Nếu không có API Key, fallback chế độ mock test
        if not self.api_key:
            latency_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                trace_id=payload.trace_id,
                content=f"[Gemini Mock Response for {payload.agent_key}]: Objective analyzed and recommendations formulated.",
                usage=TokenUsage(prompt_tokens=180, completion_tokens=95, total_tokens=275, cost_usd=0.000056),
                finish_reason="stop",
                latency_ms=max(latency_ms, 40),
            )

        # Chuẩn bị contents format của Gemini
        contents = []
        system_instruction = None
        for msg in payload.messages:
            if msg.role == ModelRole.SYSTEM:
                system_instruction = {"parts": [{"text": msg.content}]}
            else:
                role_str = "user" if msg.role == ModelRole.USER else "model"
                contents.append({"role": role_str, "parts": [{"text": msg.content}]})

        req_body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": payload.temperature,
                "maxOutputTokens": payload.max_tokens,
            }
        }
        if system_instruction:
            req_body["systemInstruction"] = system_instruction

        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=req_body)
            resp.raise_for_status()
            data = resp.json()

        latency_ms = int((time.time() - start_time) * 1000)
        candidates = data.get("candidates", [])
        content_text = ""
        finish_reason = "stop"

        if candidates:
            cand = candidates[0]
            finish_reason = cand.get("finishReason", "stop").lower()
            parts = cand.get("content", {}).get("parts", [])
            for part in parts:
                if "text" in part:
                    content_text += part["text"]

        usage_meta = data.get("usageMetadata", {})
        prompt_tok = usage_meta.get("promptTokenCount", 0)
        compl_tok = usage_meta.get("candidatesTokenCount", 0)
        cost = self.estimate_cost(model, prompt_tok, compl_tok)

        return ExecutionResult(
            trace_id=payload.trace_id,
            content=content_text,
            usage=TokenUsage(prompt_tokens=prompt_tok, completion_tokens=compl_tok, total_tokens=prompt_tok + compl_tok, cost_usd=cost),
            finish_reason=finish_reason,
            latency_ms=latency_ms,
            raw_response=data,
        )

    async def check_capability(self) -> Dict[str, Any]:
        """Kiểm tra tính sẵn sàng và capabilities của Google Gemini / ADK."""
        return {
            "runtime": "gemini",
            "provider": "google",
            "installed": True,
            "authenticated": bool(self.api_key),
            "headless_supported": True,
            "mcp_available": True,
            "workspace_access": False,
            "models": list(self.PRICING.keys()),
        }

    async def cancel(self, run_id: str) -> bool:
        return True

    async def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy" if self.api_key else "mock_ready",
            "adapter": "GeminiAdapter",
            "provider": "google",
            "authenticated": bool(self.api_key),
        }

    async def stream(self, payload: ExecutionPayload) -> AsyncIterator[str]:
        res = await self.execute(payload)
        yield res.content
