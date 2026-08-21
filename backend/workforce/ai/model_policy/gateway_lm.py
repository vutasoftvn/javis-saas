"""dspy.LM subclass sharing ModelGateway's circuit breakers across DSPy calls.

Ensures a provider outage detected via ModelGateway.invoke() also fast-fails DSPy
program calls to the same provider, and vice versa -- one shared failure signal
instead of two independent, uncoordinated retry/circuit-breaker stacks.
"""

import logging

from workforce.agents.reliability.model_gateway import ModelGateway

try:
    import dspy
except ImportError:
    dspy = None

logger = logging.getLogger(__name__)


if dspy is not None:

    class GatewayLM(dspy.LM):
        """dspy.LM that routes through ModelGateway's shared CircuitBreaker registry."""

        def forward(self, prompt=None, messages=None, **kwargs):
            provider = self.model.split("/", 1)[0] if "/" in self.model else "unknown"
            breaker = ModelGateway.get_circuit_breaker(provider)

            if not breaker.can_execute():
                raise ConnectionError(
                    f"Circuit breaker '{provider}' is OPEN (shared with ModelGateway). "
                    "Fast-failing DSPy request."
                )

            try:
                result = super().forward(prompt=prompt, messages=messages, **kwargs)
            except Exception:
                breaker.record_failure()
                raise

            breaker.record_success()
            return result

else:
    GatewayLM = None
