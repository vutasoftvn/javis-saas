"""Moved to cosa_core.telemetry (2026-08-22). Shim giữ cho các import cũ."""
from cosa_core.telemetry import *  # noqa: F401,F403
from cosa_core.telemetry import (  # noqa: F401
    SENSITIVE_KEYS,
    HAS_OTEL,
    configure_telemetry,
    filter_attributes,
    logger,
    sanitize_attribute_value,
    trace_span,
    tracer,
)
