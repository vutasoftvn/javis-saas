from datetime import datetime, timezone
import logging
import time
from typing import Any, Callable, Dict, Literal, Optional
from pydantic import BaseModel, Field

from workforce.agents.reliability.model_profiles import ModelProfile, ModelProfileRegistry
from workforce.agents.reliability.reliability import CircuitBreaker, CostTracker, RetryPolicy
from core.telemetry import trace_span

logger = logging.getLogger(__name__)


class ModelMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ModelToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ModelUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class ModelRequest(BaseModel):
    """Typed request contract for ModelGateway.invoke() (thay cho prompt: str rời rạc).

    Cố định lại 3 bug đã verify ở contract cũ: system_instruction không tới
    invoker_fn, content bị ép str(raw_res), token usage ước lượng bằng
    len(prompt.split()).
    """
    messages: list[ModelMessage]
    system_instruction: Optional[str] = None
    tools: list[Dict[str, Any]] = Field(default_factory=list)
    response_schema: Optional[Dict[str, Any]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def flattened_prompt(self) -> str:
        """Nối các message thành 1 chuỗi — chỉ dùng cho default mock generator
        và cho ước lượng token khi invoker_fn không trả usage thật."""
        return "\n".join(f"{m.role}: {m.content}" for m in self.messages)


class ModelResponse(BaseModel):
    content: str
    tool_calls: list[ModelToolCall] = Field(default_factory=list)
    usage: ModelUsage = Field(default_factory=ModelUsage)
    provider: str
    model: str
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelGatewayResult(BaseModel):
    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    latency_ms: int = 0
    fallback_used: bool = False
    status: str = "success"
    error: Optional[str] = None


class ModelGateway:
    """Central gateway for all agentic model invocations enforcing profiles, retries, circuit breakers, and fallbacks."""

    _CIRCUIT_BREAKERS: Dict[str, CircuitBreaker] = {}

    @classmethod
    def get_circuit_breaker(cls, provider: str) -> CircuitBreaker:
        if provider not in cls._CIRCUIT_BREAKERS:
            cls._CIRCUIT_BREAKERS[provider] = CircuitBreaker(name=provider, failure_threshold=3, recovery_timeout_seconds=10.0)
        return cls._CIRCUIT_BREAKERS[provider]

    @classmethod
    async def invoke(
        cls,
        request: ModelRequest,
        profile_name: str = "chat_fast",
        invoker_fn: Optional[Callable[[str, str, ModelRequest], Any]] = None,
    ) -> ModelGatewayResult:
        with trace_span("model_gateway.invoke", {"profile_name": profile_name, "message_count": len(request.messages)}):
            return await cls._invoke_internal(request, profile_name, invoker_fn)

    @classmethod
    async def _invoke_internal(
        cls,
        request: ModelRequest,
        profile_name: str,
        invoker_fn: Optional[Callable[[str, str, ModelRequest], Any]],
    ) -> ModelGatewayResult:
        profile = ModelProfileRegistry.get_profile(profile_name)
        start_time = time.monotonic()
        primary_cb = cls.get_circuit_breaker(profile.primary_provider)

        async def _call(provider: str, model: str) -> ModelResponse:
            if invoker_fn:
                return await invoker_fn(provider, model, request)
            # Default mock generator (không có invoker_fn thật, dùng cho dev/test) -
            # KHÔNG gọi network thật, giữ nguyên hành vi mock trước đây.
            prompt_preview = request.flattened_prompt()[:30]
            return ModelResponse(
                content=f"[{provider}:{model}] Response to: {prompt_preview}",
                usage=ModelUsage(
                    input_tokens=len(request.flattened_prompt().split())
                    + (len(request.system_instruction.split()) if request.system_instruction else 0),
                    output_tokens=0,
                ),
                provider=provider,
                model=model,
            )

        async def _call_primary() -> ModelResponse:
            return await _call(profile.primary_provider, profile.primary_model)

        try:
            raw_res = await RetryPolicy.execute_with_backoff(
                fn=_call_primary,
                delays=[0.05, 0.1],
                circuit_breaker=primary_cb,
            )
            latency = int((time.monotonic() - start_time) * 1000)
            cost = CostTracker.calculate_cost(profile, raw_res.usage.input_tokens, raw_res.usage.output_tokens)
            return ModelGatewayResult(
                content=raw_res.content,
                provider=raw_res.provider,
                model=raw_res.model,
                input_tokens=raw_res.usage.input_tokens,
                output_tokens=raw_res.usage.output_tokens,
                estimated_cost=cost,
                latency_ms=latency,
                fallback_used=False,
            )
        except Exception as primary_exc:
            logger.warning(f"[ModelGateway] Primary provider '{profile.primary_provider}' failed: {primary_exc}")

            if profile.fallback_provider and profile.fallback_model:
                fallback_cb = cls.get_circuit_breaker(profile.fallback_provider)
                try:
                    async def _call_fallback() -> ModelResponse:
                        return await _call(profile.fallback_provider, profile.fallback_model)

                    raw_fallback = await RetryPolicy.execute_with_backoff(
                        fn=_call_fallback,
                        delays=[0.05, 0.1],
                        circuit_breaker=fallback_cb,
                    )

                    latency = int((time.monotonic() - start_time) * 1000)
                    cost = CostTracker.calculate_cost(profile, raw_fallback.usage.input_tokens, raw_fallback.usage.output_tokens)
                    logger.info(f"[ModelGateway] Successfully failed over to fallback provider '{profile.fallback_provider}'.")
                    return ModelGatewayResult(
                        content=raw_fallback.content,
                        provider=raw_fallback.provider,
                        model=raw_fallback.model,
                        input_tokens=raw_fallback.usage.input_tokens,
                        output_tokens=raw_fallback.usage.output_tokens,
                        estimated_cost=cost,
                        latency_ms=latency,
                        fallback_used=True,
                    )
                except Exception as fallback_exc:
                    logger.error(f"[ModelGateway] Fallback provider also failed: {fallback_exc}")
                    latency = int((time.monotonic() - start_time) * 1000)
                    return ModelGatewayResult(
                        content="",
                        provider=profile.fallback_provider,
                        model=profile.fallback_model,
                        latency_ms=latency,
                        fallback_used=True,
                        status="failed",
                        error=f"Both primary ({primary_exc}) and fallback ({fallback_exc}) failed",
                    )

            latency = int((time.monotonic() - start_time) * 1000)
            return ModelGatewayResult(
                content="",
                provider=profile.primary_provider,
                model=profile.primary_model,
                latency_ms=latency,
                fallback_used=False,
                status="failed",
                error=str(primary_exc),
            )

