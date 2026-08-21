import asyncio
import time
from typing import Any
import pytest
from workforce.agents.reliability.model_profiles import ModelProfile, ModelProfileRegistry
from workforce.agents.reliability.reliability import CircuitBreaker, CircuitState, RetryPolicy, CostTracker
from workforce.agents.reliability.model_gateway import (
    ModelGateway,
    ModelGatewayResult,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelToolCall,
    ModelUsage,
)


def test_circuit_breaker_state_transitions():
    cb = CircuitBreaker(name="test_provider", failure_threshold=2, recovery_timeout_seconds=0.1)

    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # 1. First failure
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    assert cb.consecutive_failures == 1

    # 2. Second failure -> crosses threshold -> OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # 3. Wait for recovery timeout
    import time
    time.sleep(0.15)
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # 4. Success closes the circuit
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.consecutive_failures == 0


@pytest.mark.asyncio
async def test_retry_policy_exponential_backoff_transient():
    call_count = 0

    async def flaky_api_call():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("429 Too Many Requests: Rate limit exceeded")
        return "SUCCESS_AFTER_RETRY"

    result = await RetryPolicy.execute_with_backoff(
        fn=flaky_api_call,
        delays=[0.01, 0.02, 0.05],
    )
    assert result == "SUCCESS_AFTER_RETRY"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_policy_aborts_immediately_on_permanent_error():
    call_count = 0

    async def forbidden_call():
        nonlocal call_count
        call_count += 1
        raise PermissionError("403 Forbidden: Policy Violation")

    with pytest.raises(PermissionError):
        await RetryPolicy.execute_with_backoff(
            fn=forbidden_call,
            delays=[0.01, 0.02],
        )

    # Should NOT retry
    assert call_count == 1


def test_cost_tracker_calculation():
    profile = ModelProfile(
        name="test_profile",
        description="Test",
        primary_provider="test",
        primary_model="test-m",
        cost_per_1k_input=0.001,
        cost_per_1k_output=0.002,
    )

    cost = CostTracker.calculate_cost(profile, input_tokens=1000, output_tokens=500)
    # (1000/1000)*0.001 + (500/1000)*0.002 = 0.001 + 0.001 = 0.002
    assert cost == 0.002


@pytest.mark.asyncio
async def test_model_gateway_primary_success():
    req = ModelRequest(messages=[ModelMessage(role="user", content="Explain market dynamics")])
    res = await ModelGateway.invoke(request=req, profile_name="chat_fast")
    assert res.status == "success"
    assert res.provider == "deepseek"
    assert res.fallback_used is False
    assert res.input_tokens > 0


@pytest.mark.asyncio
async def test_model_gateway_automatic_fallback():
    async def mock_invoker(provider: str, model: str, request: ModelRequest) -> ModelResponse:
        if provider == "deepseek":
            raise TimeoutError("504 Gateway Timeout: DeepSeek primary timed out")
        return ModelResponse(
            content=f"Fallback from {provider}:{model}",
            usage=ModelUsage(input_tokens=12, output_tokens=4),
            provider=provider,
            model=model,
        )

    req = ModelRequest(messages=[ModelMessage(role="user", content="Synthesize strategic plan")])
    res = await ModelGateway.invoke(request=req, profile_name="reasoning", invoker_fn=mock_invoker)
    assert res.status == "success"
    assert res.fallback_used is True
    assert res.provider == "anthropic"
    assert "claude" in res.model
    assert "Fallback from anthropic" in res.content


@pytest.mark.asyncio
async def test_model_gateway_passes_system_instruction_to_invoker():
    """Bug đã verify: system_instruction trước đây KHÔNG BAO GIỜ tới invoker_fn,
    chỉ dùng để ước lượng token. Giờ nó phải nằm trong request.system_instruction
    mà invoker_fn nhận được nguyên vẹn."""
    seen: dict[str, Any] = {}

    async def capturing_invoker(provider: str, model: str, request: ModelRequest) -> ModelResponse:
        seen["system_instruction"] = request.system_instruction
        return ModelResponse(
            content="ok",
            usage=ModelUsage(input_tokens=1, output_tokens=1),
            provider=provider,
            model=model,
        )

    req = ModelRequest(
        messages=[ModelMessage(role="user", content="hi")],
        system_instruction="Bạn là Chief of Staff của founder.",
    )
    await ModelGateway.invoke(request=req, profile_name="chat_fast", invoker_fn=capturing_invoker)
    assert seen["system_instruction"] == "Bạn là Chief of Staff của founder."


def test_model_request_response_shapes():
    from workforce.agents.reliability.model_gateway import (
        ModelMessage,
        ModelRequest,
        ModelResponse,
        ModelToolCall,
        ModelUsage,
    )
    req = ModelRequest(
        messages=[ModelMessage(role="user", content="hello")],
        system_instruction="You are a helpful assistant.",
    )
    assert req.tools == []
    assert req.response_schema is None
    assert req.stream is False
    assert req.metadata == {}

    resp = ModelResponse(
        content="hi there",
        usage=ModelUsage(input_tokens=5, output_tokens=3),
        provider="deepseek",
        model="deepseek-chat",
    )
    assert resp.tool_calls == []
    assert resp.finish_reason == "stop"

    tc = ModelToolCall(id="call_1", name="finance_get_financial_summary", arguments={"workspace_id": 1})
    assert tc.arguments["workspace_id"] == 1

