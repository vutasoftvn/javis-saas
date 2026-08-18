import asyncio
import pytest
from app.workforce.agents.reliability.model_profiles import ModelProfile, ModelProfileRegistry
from app.workforce.agents.reliability.reliability import CircuitBreaker, CircuitState, RetryPolicy, CostTracker
from app.workforce.agents.reliability.model_gateway import ModelGateway, ModelGatewayResult


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
    res = await ModelGateway.invoke(
        prompt="Explain market dynamics",
        profile_name="chat_fast",
    )
    assert res.status == "success"
    assert res.provider == "deepseek"
    assert res.fallback_used is False
    assert res.input_tokens > 0


@pytest.mark.asyncio
async def test_model_gateway_automatic_fallback():
    async def mock_invoker(provider: str, model: str, prompt: str):
        if provider == "deepseek":
            raise TimeoutError("504 Gateway Timeout: DeepSeek primary timed out")
        return f"Fallback from {provider}:{model}"

    res = await ModelGateway.invoke(
        prompt="Synthesize strategic plan",
        profile_name="reasoning",
        invoker_fn=mock_invoker,
    )
    assert res.status == "success"
    assert res.fallback_used is True
    assert res.provider == "anthropic"
    assert "claude" in res.model
    assert "Fallback from anthropic" in res.content
