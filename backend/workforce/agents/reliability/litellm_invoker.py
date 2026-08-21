"""Điểm kết nối LiteLLM duy nhất dùng chung bởi ModelGateway (qua invoker_fn) và
CosaModelGatewayLlm (ADK model adapter) — tránh 2 cách kết nối LiteLLM trôi dạt
khác nhau (xem Quyết định 1, mục "Model connectivity").

GatewayLM (backend/app/workforce/ai/model_policy/gateway_lm.py) KHÔNG đổi sang gọi
hàm này — nó đã dùng litellm sẵn qua dspy.LM.forward() nội bộ và đã chia sẻ đúng
CircuitBreaker registry với ModelGateway qua ModelGateway.get_circuit_breaker();
viết lại forward() của nó là thay đổi rủi ro không cần thiết nằm ngoài phạm vi sửa
lỗi ModelGateway.invoke().
"""
import logging
from typing import Any

import litellm

from workforce.agents.reliability.model_gateway import (
    ModelRequest,
    ModelResponse,
    ModelToolCall,
    ModelUsage,
)

logger = logging.getLogger(__name__)


def _to_litellm_messages(request: ModelRequest) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if request.system_instruction:
        messages.append({"role": "system", "content": request.system_instruction})
    messages.extend({"role": m.role, "content": m.content} for m in request.messages)
    return messages


async def cosa_litellm_invoker(provider: str, model: str, request: ModelRequest) -> ModelResponse:
    """invoker_fn thật cho ModelGateway.invoke() — gọi litellm.acompletion() với quy
    ước đặt tên "provider/model" (đúng quy ước gateway_lm.py đã dùng)."""
    kwargs: dict[str, Any] = {
        "model": f"{provider}/{model}",
        "messages": _to_litellm_messages(request),
    }
    if request.temperature is not None:
        kwargs["temperature"] = request.temperature
    if request.max_tokens is not None:
        kwargs["max_tokens"] = request.max_tokens
    if request.tools:
        kwargs["tools"] = request.tools
    if request.response_schema is not None:
        kwargs["response_format"] = request.response_schema

    raw = await litellm.acompletion(**kwargs)
    choice = raw.choices[0]
    tool_calls = [
        ModelToolCall(id=tc.id, name=tc.function.name, arguments=tc.function.arguments or {})
        for tc in (choice.message.tool_calls or [])
    ] if getattr(choice.message, "tool_calls", None) else []

    return ModelResponse(
        content=choice.message.content or "",
        tool_calls=tool_calls,
        usage=ModelUsage(
            input_tokens=getattr(raw.usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(raw.usage, "completion_tokens", 0) or 0,
        ),
        provider=provider,
        model=model,
        finish_reason=choice.finish_reason or "stop",
    )
