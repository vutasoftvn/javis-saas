from __future__ import annotations

import os
import time
from typing import Any, Optional

from opentelemetry import context as otel_context
from opentelemetry import trace as otel_trace_api
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import NonRecordingSpan, SpanContext, SpanKind, TraceFlags
from pydantic import BaseModel, Field


class OtelSpan(BaseModel):
    """Facade view over a real `opentelemetry.sdk.trace.Span` (§20.2).

    Kept as the public shape callers already depend on (trace_id/span_id as hex
    strings, `correlation_id`/`workspace_id` as first-class fields) so call
    sites don't need to change when the exporter backing this changes.
    """

    trace_id: str
    span_id: str
    name: str
    parent_span_id: Optional[str] = None
    correlation_id: Optional[str] = None
    workspace_id: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    start_time_ns: int = Field(default_factory=time.time_ns)
    end_time_ns: Optional[int] = None
    status: str = "OK"


def _new_span_context(trace_id_hex: Optional[str]) -> Optional[SpanContext]:
    """Build a `SpanContext` carrying a caller-supplied trace_id so children
    started with `trace_id=parent.trace_id` land in the same OTEL trace, even
    though this facade's imperative `start_span(trace_id=..., parent_span_id=...)`
    API (used across `agentos/`) predates using a real `with ... as current_span`
    context-manager style."""
    if not trace_id_hex:
        return None
    try:
        trace_id_int = int(trace_id_hex, 16)
    except ValueError:
        return None
    if trace_id_int == 0:
        return None
    return SpanContext(
        trace_id=trace_id_int,
        span_id=otel_trace_api.INVALID_SPAN_ID,
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )


class OtelTracer:
    """OpenTelemetry Distributed Tracer (§20.2) — thật, dùng `opentelemetry-sdk`.

    Mặc định dùng `InMemorySpanExporter` (phục vụ `get_spans()` cục bộ, không
    cần hạ tầng) + `ConsoleSpanExporter` (stdout, an toàn tuyệt đối, không
    phụ thuộc hạ tầng nào). Chưa cắm OTLP/Jaeger exporter thật vì roadmap yêu
    cầu xác nhận hạ tầng ở `infra/` trước (`opentelemetry-exporter-otlp-*`
    hiện chưa có trong `agentos/requirements.txt`) — set biến môi trường
    `OTEL_EXPORTER_OTLP_ENDPOINT` khi đã có quyết định, xem `_maybe_add_otlp_exporter()`.

    `correlation_id` map vào span như 1 attribute (không dùng làm `trace_id`
    thật của OTEL — OTEL yêu cầu 128-bit int, `correlation_id` là string tự
    do) — đúng như phương án roadmap 10d.3 cho phép khi 2 format ID không
    tương thích.
    """

    def __init__(self, service_name: str = "agentos") -> None:
        self.service_name = service_name
        self._in_memory_exporter = InMemorySpanExporter()
        self._provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        self._provider.add_span_processor(SimpleSpanProcessor(self._in_memory_exporter))
        self._provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        self._maybe_add_otlp_exporter()
        self._tracer = self._provider.get_tracer(service_name)
        self._open_spans: dict[str, Any] = {}  # span_id_hex -> real SDK span

    def _maybe_add_otlp_exporter(self) -> None:
        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if not endpoint:
            return
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        except ImportError:
            return
        self._provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))

    def start_span(
        self,
        name: str,
        *,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        attributes: Optional[dict[str, Any]] = None,
    ) -> OtelSpan:
        parent_span_context = _new_span_context(trace_id)
        ctx: Optional[otel_context.Context] = None
        if parent_span_context is not None:
            ctx = otel_trace_api.set_span_in_context(NonRecordingSpan(parent_span_context))

        real_span = self._tracer.start_span(name, context=ctx, kind=SpanKind.INTERNAL)

        attrs = dict(attributes or {})
        if correlation_id:
            attrs["correlation_id"] = correlation_id
            real_span.set_attribute("correlation_id", correlation_id)
        if workspace_id:
            real_span.set_attribute("workspace_id", workspace_id)
        for key, value in attrs.items():
            if key in ("correlation_id",):
                continue
            real_span.set_attribute(key, value if isinstance(value, (str, int, float, bool)) else str(value))

        span_id_hex = format(real_span.get_span_context().span_id, "032x")
        trace_id_hex = format(real_span.get_span_context().trace_id, "032x")
        self._open_spans[span_id_hex] = real_span

        return OtelSpan(
            trace_id=trace_id_hex,
            span_id=span_id_hex,
            name=name,
            parent_span_id=parent_span_id,
            correlation_id=correlation_id,
            workspace_id=workspace_id,
            attributes=attrs,
            start_time_ns=real_span.start_time,
        )

    def end_span(self, span: OtelSpan, status: str = "OK", **attributes: Any) -> None:
        real_span = self._open_spans.pop(span.span_id, None)
        if real_span is None:
            return
        for key, value in attributes.items():
            real_span.set_attribute(key, value if isinstance(value, (str, int, float, bool)) else str(value))
        # `status` here is an arbitrary caller-defined label (e.g. "COMPLETED"/"FAILED"),
        # not OTEL's binary OK/ERROR status code — keep it verbatim as an attribute and
        # only derive the real OTEL status code as a coarse ERROR/OK signal.
        real_span.set_attribute("agentos.status", status)
        is_error = "FAIL" in status.upper() or "ERROR" in status.upper()
        real_span.set_status(
            otel_trace_api.Status(otel_trace_api.StatusCode.ERROR if is_error else otel_trace_api.StatusCode.OK)
        )
        real_span.end()

        span.end_time_ns = real_span.end_time
        span.status = status
        span.attributes.update(attributes)

    def get_spans(self, *, trace_id: Optional[str] = None, correlation_id: Optional[str] = None) -> list[OtelSpan]:
        finished: list[ReadableSpan] = list(self._in_memory_exporter.get_finished_spans())
        matched = [self._to_otel_span(s) for s in finished]
        if trace_id:
            matched = [s for s in matched if s.trace_id == trace_id]
        if correlation_id:
            matched = [s for s in matched if s.correlation_id == correlation_id]
        return matched

    def _to_otel_span(self, s: ReadableSpan) -> OtelSpan:
        ctx = s.get_span_context()
        parent = s.parent
        attrs = dict(s.attributes or {})
        status_str = attrs.get("agentos.status") or (
            "OK" if s.status.status_code == otel_trace_api.StatusCode.OK else s.status.status_code.name
        )
        return OtelSpan(
            trace_id=format(ctx.trace_id, "032x"),
            span_id=format(ctx.span_id, "032x"),
            name=s.name,
            parent_span_id=format(parent.span_id, "032x") if parent is not None else None,
            correlation_id=attrs.get("correlation_id"),
            workspace_id=attrs.get("workspace_id"),
            attributes=attrs,
            start_time_ns=s.start_time or 0,
            end_time_ns=s.end_time,
            status=status_str,
        )

    def clear(self) -> None:
        self._in_memory_exporter.clear()
        self._open_spans.clear()


# Global singleton tracer
_default_otel_tracer = OtelTracer()


def get_otel_tracer() -> OtelTracer:
    return _default_otel_tracer
