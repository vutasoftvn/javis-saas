from __future__ import annotations

import os
from typing import Any

import prometheus_client
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

__all__ = [
    "CONTENT_TYPE_LATEST",
    "REGISTRY",
    "COSA_APPROVALS_TOTAL",
    "COSA_APPROVAL_WAIT_SECONDS",
    "COSA_MODEL_COST_USD_TOTAL",
    "COSA_MODEL_TOKENS_TOTAL",
    "COSA_RUNS_TOTAL",
    "COSA_RUN_DURATION_SECONDS",
    "COSA_SCHEDULER_QUEUE_DEPTH",
    "COSA_TOOL_CALLS_TOTAL",
    "COSA_TOOL_CALL_DURATION_SECONDS",
    "COSA_WORKER_ACTIVE_LEASES",
    "dec_active_leases",
    "get_prometheus_metrics_payload",
    "inc_active_leases",
    "record_approval",
    "record_model_tokens",
    "record_run_outcome",
    "record_tool_call",
    "set_active_leases",
    "set_scheduler_queue_depth",
]

REGISTRY = prometheus_client.REGISTRY

# Default estimated pricing (USD per 1 Million tokens)
DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "deepseek": {
        "prompt": float(os.environ.get("DEEPSEEK_PRICE_PROMPT_PER_M", "0.14")),
        "completion": float(os.environ.get("DEEPSEEK_PRICE_COMPLETION_PER_M", "0.28")),
    },
    "openai": {
        "prompt": float(os.environ.get("OPENAI_PRICE_PROMPT_PER_M", "2.50")),
        "completion": float(os.environ.get("OPENAI_PRICE_COMPLETION_PER_M", "10.00")),
    },
    "default": {
        "prompt": float(os.environ.get("MODEL_DEFAULT_PRICE_PROMPT_PER_M", "0.50")),
        "completion": float(os.environ.get("MODEL_DEFAULT_PRICE_COMPLETION_PER_M", "1.50")),
    },
}

# --- Counters ---
COSA_RUNS_TOTAL = Counter(
    "cosa_runs_total",
    "Total number of agent execution runs partitioned by outcome.",
    ["outcome"],
    registry=REGISTRY,
)

COSA_TOOL_CALLS_TOTAL = Counter(
    "cosa_tool_calls_total",
    "Total number of capability tool calls partitioned by capability and outcome.",
    ["capability", "outcome"],
    registry=REGISTRY,
)

COSA_MODEL_TOKENS_TOTAL = Counter(
    "cosa_model_tokens_total",
    "Total number of model tokens consumed partitioned by direction and model.",
    ["direction", "model"],
    registry=REGISTRY,
)

COSA_APPROVALS_TOTAL = Counter(
    "cosa_approvals_total",
    "Total number of human approvals partitioned by decision.",
    ["decision"],
    registry=REGISTRY,
)

COSA_MODEL_COST_USD_TOTAL = Counter(
    "cosa_model_cost_usd_total",
    "Estimated total cost in USD for model token usage partitioned by model.",
    ["model"],
    registry=REGISTRY,
)

# --- Histograms ---
COSA_RUN_DURATION_SECONDS = Histogram(
    "cosa_run_duration_seconds",
    "Duration of agent execution runs in seconds.",
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
    registry=REGISTRY,
)

COSA_APPROVAL_WAIT_SECONDS = Histogram(
    "cosa_approval_wait_seconds",
    "Wait time for human approvals in seconds.",
    buckets=(1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0),
    registry=REGISTRY,
)

COSA_TOOL_CALL_DURATION_SECONDS = Histogram(
    "cosa_tool_call_duration_seconds",
    "Execution duration of capability tool calls in seconds.",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
    registry=REGISTRY,
)

# --- Gauges ---
COSA_WORKER_ACTIVE_LEASES = Gauge(
    "cosa_worker_active_leases",
    "Number of active execution leases currently held by workers.",
    registry=REGISTRY,
)

COSA_SCHEDULER_QUEUE_DEPTH = Gauge(
    "cosa_scheduler_queue_depth",
    "Number of scheduled tasks currently pending or claimed in queue.",
    registry=REGISTRY,
)


def record_run_outcome(outcome: str, duration_sec: float | None = None) -> None:
    """Ghi nhận outcome của 1 Run (completed, failed, waiting_approval, cancelled)
    và thời lượng thực thi."""
    norm_outcome = str(outcome).lower()
    COSA_RUNS_TOTAL.labels(outcome=norm_outcome).inc()
    if duration_sec is not None and duration_sec >= 0:
        COSA_RUN_DURATION_SECONDS.observe(duration_sec)


def record_tool_call(
    capability: str,
    outcome: str,
    duration_sec: float | None = None,
) -> None:
    """Ghi nhận outcome của 1 capability tool call (success, failed, waiting_approval, denied)
    và thời lượng thực thi."""
    norm_outcome = str(outcome).lower()
    COSA_TOOL_CALLS_TOTAL.labels(capability=capability, outcome=norm_outcome).inc()
    if duration_sec is not None and duration_sec >= 0:
        COSA_TOOL_CALL_DURATION_SECONDS.observe(duration_sec)


def record_approval(decision: str, wait_duration_sec: float | None = None) -> None:
    """Ghi nhận quyết định phê duyệt (approved, rejected, expired, timeout)
    và thời gian chờ từ lúc yêu cầu."""
    norm_decision = str(decision).lower()
    COSA_APPROVALS_TOTAL.labels(decision=norm_decision).inc()
    if wait_duration_sec is not None and wait_duration_sec >= 0:
        COSA_APPROVAL_WAIT_SECONDS.observe(wait_duration_sec)


def record_model_tokens(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    """Ghi nhận số token model sử dụng (input/output) và ước lượng chi phí USD."""
    norm_model = str(model or "deepseek-chat").lower()
    p_tokens = max(0, prompt_tokens)
    c_tokens = max(0, completion_tokens)

    if p_tokens > 0:
        COSA_MODEL_TOKENS_TOTAL.labels(direction="input", model=norm_model).inc(p_tokens)
    if c_tokens > 0:
        COSA_MODEL_TOKENS_TOTAL.labels(direction="output", model=norm_model).inc(c_tokens)

    # Calculate estimated cost
    pricing_family = "default"
    if "deepseek" in norm_model:
        pricing_family = "deepseek"
    elif "gpt" in norm_model or "openai" in norm_model:
        pricing_family = "openai"

    p_rate = DEFAULT_PRICING[pricing_family]["prompt"]
    c_rate = DEFAULT_PRICING[pricing_family]["completion"]
    cost = (p_tokens / 1_000_000.0 * p_rate) + (c_tokens / 1_000_000.0 * c_rate)

    if cost > 0:
        COSA_MODEL_COST_USD_TOTAL.labels(model=norm_model).inc(cost)


def set_active_leases(count: int) -> None:
    """Cập nhật số lượng lease đang active."""
    COSA_WORKER_ACTIVE_LEASES.set(max(0, count))


def inc_active_leases(amount: int = 1) -> None:
    """Tăng số lượng lease active."""
    COSA_WORKER_ACTIVE_LEASES.inc(amount)


def dec_active_leases(amount: int = 1) -> None:
    """Giảm số lượng lease active."""
    COSA_WORKER_ACTIVE_LEASES.dec(amount)


def set_scheduler_queue_depth(depth: int) -> None:
    """Cập nhật độ sâu hàng đợi scheduler."""
    COSA_SCHEDULER_QUEUE_DEPTH.set(max(0, depth))


def get_prometheus_metrics_payload() -> tuple[bytes, str]:
    """Sinh payload Prometheus text exposition format và Content-Type header."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
