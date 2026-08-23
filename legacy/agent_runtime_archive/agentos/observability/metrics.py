# backend/agentos/observability/metrics.py
from __future__ import annotations

from pydantic import BaseModel

from agentos.core.models import AgentRun
from agentos.observability.pricing import PricingTable, estimate_cost_usd


class RunMetrics(BaseModel):
    latency_seconds: float
    span_count: int
    tool_call_count: int
    input_tokens: int
    output_tokens: int
    cost_usd: float | None = None


def compute_run_metrics(
    run: AgentRun, spans: list[dict], pricing_table: PricingTable | None = None
) -> RunMetrics:
    """Tính observability metrics thuần từ dữ liệu đã ghi sẵn — không thêm
    instrumentation mới, chỉ đọc lại các span `model_generation.completed`
    mà Executor đã ghi. Blueprint §56 muốn token in/out và cost per outcome;
    số token lấy từ usage thật do provider trả về (TokenUsage trong
    agentos/core/model_provider.py), cộng dồn qua mọi lần gọi model trong
    run. `cost_usd` luôn là None trừ khi caller truyền `pricing_table` có
    giá thật cho (các) model đã dùng — xem agentos/observability/pricing.py
    để hiểu vì sao không có mức giá cứng ở đây.
    """
    latency_seconds = (run.updated_at - run.created_at).total_seconds()
    tool_call_count = sum(1 for span in spans if span["name"] == "tool_call.completed")

    generation_spans = [span for span in spans if span["name"] == "model_generation.completed"]
    input_tokens = sum(span.get("input_tokens") or 0 for span in generation_spans)
    output_tokens = sum(span.get("output_tokens") or 0 for span in generation_spans)

    cost_usd: float | None = None
    if pricing_table:
        costs = [
            estimate_cost_usd(
                span.get("model"), span.get("input_tokens") or 0, span.get("output_tokens") or 0, pricing_table
            )
            for span in generation_spans
        ]
        priced = [c for c in costs if c is not None]
        # Chỉ báo tổng cost khi MỌI span generation trong run đều có giá —
        # cộng dồn một phần sẽ âm thầm báo thiếu cost cho run pha trộn model
        # đã định giá và model chưa định giá.
        if priced and len(priced) == len(generation_spans):
            cost_usd = sum(priced)

    return RunMetrics(
        latency_seconds=latency_seconds,
        span_count=len(spans),
        tool_call_count=tool_call_count,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
    )
