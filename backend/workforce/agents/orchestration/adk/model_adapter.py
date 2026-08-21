# backend/app/workforce/agents/orchestration/adk/model_adapter.py
"""ADK BaseLlm adapter gọi ModelGateway.invoke() thay vì google.adk.models.lite_llm.LiteLlm
trực tiếp — giữ nguyên retry/circuit-breaker/cost-tracking của ModelGateway, và ADK
không tự quản lý kết nối model provider (xem Quyết định 1, mục "Model connectivity")."""
from collections.abc import AsyncGenerator
from typing import Any

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types as genai_types

from workforce.agents.reliability.litellm_invoker import cosa_litellm_invoker
from workforce.agents.reliability.model_gateway import ModelGateway, ModelMessage, ModelRequest


def _extract_text(content: genai_types.Content | None) -> str:
    if content is None or not content.parts:
        return ""
    texts = []
    for p in content.parts:
        if getattr(p, "text", None):
            texts.append(p.text)
    return "\n".join(texts)


def _system_instruction_text(config: genai_types.GenerateContentConfig | None) -> str | None:
    if config is None:
        return None
    raw = getattr(config, "system_instruction", None)
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw
    if isinstance(raw, genai_types.Content):
        return _extract_text(raw) or None
    return str(raw)


def _to_model_request(llm_request: LlmRequest) -> ModelRequest:
    messages = [
        ModelMessage(role="assistant" if c.role == "model" else (c.role or "user"), content=_extract_text(c))
        for c in (llm_request.contents or [])
    ]
    return ModelRequest(
        messages=messages,
        system_instruction=_system_instruction_text(llm_request.config),
        temperature=getattr(llm_request.config, "temperature", None),
        max_tokens=getattr(llm_request.config, "max_output_tokens", None),
    )


class CosaModelGatewayLlm(BaseLlm):
    """model field (BaseLlm) giữ định dạng "provider/model" (quy ước LiteLLM có sẵn
    trong codebase — xem gateway_lm.py). profile_name chọn ModelProfile
    (retry/fallback/cost) trong ModelProfileRegistry."""

    profile_name: str = "reasoning"

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        request = _to_model_request(llm_request)
        result = await ModelGateway.invoke(
            request=request,
            profile_name=self.profile_name,
            invoker_fn=cosa_litellm_invoker,
        )
        yield LlmResponse(
            content=genai_types.Content(role="model", parts=[genai_types.Part(text=result.content)]),
            finish_reason=(
                genai_types.FinishReason.STOP if result.status == "success" else genai_types.FinishReason.OTHER
            ),
            custom_metadata={
                "provider": result.provider,
                "model": result.model,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "estimated_cost": result.estimated_cost,
                "fallback_used": result.fallback_used,
            },
        )
