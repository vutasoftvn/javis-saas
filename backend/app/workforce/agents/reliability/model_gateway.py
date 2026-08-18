from datetime import datetime, timezone
import logging
import time
from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel, Field

from app.workforce.agents.reliability.model_profiles import ModelProfile, ModelProfileRegistry
from app.workforce.agents.reliability.reliability import CircuitBreaker, CostTracker, RetryPolicy
from app.core.telemetry import trace_span

logger = logging.getLogger(__name__)


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
        prompt: str,
        profile_name: str = "chat_fast",
        system_instruction: Optional[str] = None,
        invoker_fn: Optional[Callable[[str, str, str], Any]] = None,
    ) -> ModelGatewayResult:
        with trace_span("model_gateway.invoke", {"profile_name": profile_name, "prompt_len": len(prompt)}):
            return await cls._invoke_internal(prompt, profile_name, system_instruction, invoker_fn)

    @classmethod
    async def _invoke_internal(
        cls,
        prompt: str,
        profile_name: str = "chat_fast",
        system_instruction: Optional[str] = None,
        invoker_fn: Optional[Callable[[str, str, str], Any]] = None,
    ) -> ModelGatewayResult:
        profile = ModelProfileRegistry.get_profile(profile_name)
        start_time = time.monotonic()
        primary_cb = cls.get_circuit_breaker(profile.primary_provider)

        # 1. Attempt Primary Provider with Retry & Circuit Breaker
        try:
            async def _call_primary():
                if invoker_fn:
                    return await invoker_fn(profile.primary_provider, profile.primary_model, prompt)
                # Default mock generator
                return f"[{profile.primary_provider}:{profile.primary_model}] Response to: {prompt[:30]}"

            raw_res = await RetryPolicy.execute_with_backoff(
                fn=_call_primary,
                delays=[0.05, 0.1],
                circuit_breaker=primary_cb,
            )

            latency = int((time.monotonic() - start_time) * 1000)
            in_tok = len(prompt.split()) + (len(system_instruction.split()) if system_instruction else 0)
            out_tok = len(str(raw_res).split())
            cost = CostTracker.calculate_cost(profile, in_tok, out_tok)

            return ModelGatewayResult(
                content=str(raw_res),
                provider=profile.primary_provider,
                model=profile.primary_model,
                input_tokens=in_tok,
                output_tokens=out_tok,
                estimated_cost=cost,
                latency_ms=latency,
                fallback_used=False,
            )

        except Exception as primary_exc:
            logger.warning(f"[ModelGateway] Primary provider '{profile.primary_provider}' failed: {primary_exc}")

            # 2. Check if Fallback Provider is configured
            if profile.fallback_provider and profile.fallback_model:
                fallback_cb = cls.get_circuit_breaker(profile.fallback_provider)
                try:
                    async def _call_fallback():
                        if invoker_fn:
                            return await invoker_fn(profile.fallback_provider, profile.fallback_model, prompt)
                        return f"[{profile.fallback_provider}:{profile.fallback_model}] Fallback response to: {prompt[:30]}"

                    raw_fallback = await RetryPolicy.execute_with_backoff(
                        fn=_call_fallback,
                        delays=[0.05, 0.1],
                        circuit_breaker=fallback_cb,
                    )

                    latency = int((time.monotonic() - start_time) * 1000)
                    in_tok = len(prompt.split())
                    out_tok = len(str(raw_fallback).split())
                    cost = CostTracker.calculate_cost(profile, in_tok, out_tok)

                    logger.info(f"[ModelGateway] Successfully failed over to fallback provider '{profile.fallback_provider}'.")
                    return ModelGatewayResult(
                        content=str(raw_fallback),
                        provider=profile.fallback_provider,
                        model=profile.fallback_model,
                        input_tokens=in_tok,
                        output_tokens=out_tok,
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
