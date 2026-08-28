from __future__ import annotations

import contextlib
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from opentelemetry import propagate, trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.trace import Span, Status, StatusCode, Tracer

__all__ = [
    "get_current_span_id",
    "get_current_trace_id",
    "get_tracer",
    "init_tracing",
    "inject_trace_carrier",
    "sync_trace_span",
    "trace_span",
]

_TRACER_NAME = "cosa.observability"
_IS_INITIALIZED = False


def init_tracing(
    service_name: str,
    app: Any | None = None,
    *,
    force_sync_export: bool = False,
) -> TracerProvider:
    """Khởi tạo OpenTelemetry Tracing cho COSA services (API / Worker).

    - service.name, service.version, deployment.environment từ env.
    - OTEL_EXPORTER_OTLP_ENDPOINT: nếu có, cấu hình OTLPSpanExporter. Nếu không có,
      TracerProvider hoạt động no-op (không xuất network, không lỗi).
    - Tự động instrument httpx client & FastAPI (nếu truyền app).
    """
    global _IS_INITIALIZED

    env_name = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development"))
    service_version = os.environ.get("SERVICE_VERSION", "1.0.0")

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": env_name,
        }
    )

    provider = TracerProvider(resource=resource)

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter as GrpcExporter,
            )

            # Support grpc or http depending on endpoint scheme
            if otlp_endpoint.startswith("http://") or otlp_endpoint.startswith("https://"):
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter as HttpExporter,
                )

                exporter = HttpExporter(endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces")
            else:
                exporter = GrpcExporter(endpoint=otlp_endpoint)

            processor = (
                SimpleSpanProcessor(exporter)
                if force_sync_export
                else BatchSpanProcessor(exporter)
            )
            provider.add_span_processor(processor)
        except Exception:
            # Fallback to no-op if exporter creation fails
            pass

    trace.set_tracer_provider(provider)

    # Auto-instrument httpx if available
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except Exception:
        pass

    # Auto-instrument FastAPI if app is provided
    if app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        except Exception:
            pass

    _IS_INITIALIZED = True
    return provider


def get_tracer(name: str = _TRACER_NAME) -> Tracer:
    """Lấy Tracer instance từ tracer provider toàn cục."""
    return trace.get_tracer(name)


def get_current_trace_id() -> str | None:
    """Lấy trace_id dạng hex của span đang active, trả về None nếu không có."""
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return f"{span.get_span_context().trace_id:032x}"
    return None


def get_current_span_id() -> str | None:
    """Lấy span_id dạng hex của span đang active, trả về None nếu không có."""
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return f"{span.get_span_context().span_id:016x}"
    return None


def inject_trace_carrier(headers: dict[str, str] | None = None) -> dict[str, str]:
    """Chèn W3C TraceContext headers (traceparent, tracestate) vào headers dict
    để propagate trace context sang Encore / external services."""
    carrier = dict(headers or {})
    propagate.inject(carrier)
    return carrier


@asynccontextmanager
async def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    tracer_name: str = _TRACER_NAME,
) -> AsyncIterator[Span]:
    """Async context manager tạo manual span với attributes và tự động record exception."""
    tracer = get_tracer(tracer_name)
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                if v is not None:
                    span.set_attribute(k, str(v) if isinstance(v, (dict, list)) else v)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


@contextmanager
def sync_trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    tracer_name: str = _TRACER_NAME,
) -> Iterator[Span]:
    """Sync context manager tạo manual span với attributes và tự động record exception."""
    tracer = get_tracer(tracer_name)
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                if v is not None:
                    span.set_attribute(k, str(v) if isinstance(v, (dict, list)) else v)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
