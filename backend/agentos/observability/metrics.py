# backend/agentos/observability/metrics.py
from __future__ import annotations

from pydantic import BaseModel

from agentos.core.models import AgentRun


class RunMetrics(BaseModel):
    latency_seconds: float
    span_count: int
    tool_call_count: int


def compute_run_metrics(run: AgentRun, spans: list[dict]) -> RunMetrics:
    """Derive observability metrics purely from what's already recorded —
    no new instrumentation added here. Blueprint §56 token/model cost
    tracking needs real ModelProvider usage reporting, which is later
    hardening; latency and tool-call count are the metrics genuinely
    available from Phase 0/1 data as-is.
    """
    latency_seconds = (run.updated_at - run.created_at).total_seconds()
    tool_call_count = sum(1 for span in spans if span["name"] == "tool_call.completed")
    return RunMetrics(latency_seconds=latency_seconds, span_count=len(spans), tool_call_count=tool_call_count)
