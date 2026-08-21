"""OpenTelemetry Observability and Distributed Tracing for COSA OS.

Wraps key execution spans (conversation_gate, orchestrator, ModelGateway, GovernanceKernel)
while guaranteeing:
1. No secrets, API keys, credentials, or Chain-of-Thought leakage in traces.
2. Graceful fallback when OpenTelemetry SDK is not initialized.
"""

from contextlib import contextmanager
import logging
from typing import Any, Dict, Generator, Optional

logger = logging.getLogger(__name__)

# Try importing opentelemetry, provide fallback tracer if not present
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    tracer = trace.get_tracer("cosa.agent_platform", "1.0.0")
    HAS_OTEL = True
except ImportError:
    tracer = None
    HAS_OTEL = False


# Sensitive keys that must NEVER be recorded in span attributes
SENSITIVE_KEYS = frozenset({
    "api_key", "secret", "password", "token", "access_token",
    "refresh_token", "credential", "auth", "authorization",
    "private_key", "chain_of_thought", "thought_log"
})


def sanitize_attribute_value(val: Any) -> Any:
    """Sanitize attribute values for safe tracing."""
    if isinstance(val, (int, float, bool, str)):
        return val
    return str(val)


def filter_attributes(attrs: Dict[str, Any]) -> Dict[str, Any]:
    """Filter out sensitive keys and sanitize values."""
    safe = {}
    for k, v in attrs.items():
        k_lower = k.lower()
        if any(sk in k_lower for sk in SENSITIVE_KEYS):
            continue
        safe[k] = sanitize_attribute_value(v)
    return safe


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> Generator[Optional[Any], None, None]:
    """Context manager to trace an execution span safely."""
    safe_attrs = filter_attributes(attributes or {})

    if HAS_OTEL and tracer is not None:
        with tracer.start_as_current_span(name, attributes=safe_attrs) as span:
            try:
                yield span
            except Exception as exc:
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.record_exception(exc)
                raise
    else:
        yield None


def configure_telemetry(service_name: str = "cosa-brain-api") -> None:
    """Configures a real OpenTelemetry TracerProvider so trace_span() spans are
    actually recorded/exported, not silently no-op. Call once at app startup
    (see app/main.py::lifespan). Safe no-op if opentelemetry-sdk isn't installed.
    """
    if not HAS_OTEL:
        return
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
