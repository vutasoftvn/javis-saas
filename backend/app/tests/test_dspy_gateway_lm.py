import pytest

pytest.importorskip("dspy")

from unittest.mock import patch

from app.ai.model_policy.gateway_lm import GatewayLM
from app.agents.reliability.model_gateway import ModelGateway
from app.agents.reliability.reliability import CircuitState


def test_gateway_lm_shares_circuit_breaker_with_model_gateway():
    """A GatewayLM failure must trip the SAME CircuitBreaker instance ModelGateway uses
    for that provider -- proves DSPy calls and ModelGateway calls share failure state,
    instead of running two independent, uncoordinated resilience stacks."""
    ModelGateway._CIRCUIT_BREAKERS.pop("test_provider_dspy", None)

    lm = GatewayLM(model="test_provider_dspy/some-model", api_key="dummy")

    with patch("dspy.LM.forward", side_effect=RuntimeError("boom")):
        for _ in range(3):
            with pytest.raises(RuntimeError):
                lm.forward(prompt="hi")

    breaker = ModelGateway.get_circuit_breaker("test_provider_dspy")
    assert breaker.state == CircuitState.OPEN

    with pytest.raises(ConnectionError, match="Circuit breaker"):
        lm.forward(prompt="hi again")


def test_gateway_lm_records_success_and_stays_closed():
    ModelGateway._CIRCUIT_BREAKERS.pop("test_provider_dspy_ok", None)
    lm = GatewayLM(model="test_provider_dspy_ok/some-model", api_key="dummy")

    with patch("dspy.LM.forward", return_value="ok"):
        result = lm.forward(prompt="hi")

    assert result == "ok"
    breaker = ModelGateway.get_circuit_breaker("test_provider_dspy_ok")
    assert breaker.state == CircuitState.CLOSED
