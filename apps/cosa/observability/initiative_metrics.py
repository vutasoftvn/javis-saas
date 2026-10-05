"""Prometheus metrics for AI Initiative runtime observability and review cadence (Task 10).

Redaction Invariant: Metric labels MUST NEVER contain raw user prompts,
documents, messages, tool payload, or credentials.
Labels are strictly scoped to allowlisted governance identifiers:
initiative_id, workspace_id, state, risk_tier, autonomy_tier, gate_result.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# Allowed label names for initiative metrics
INITIATIVE_LABELS = [
    "initiative_id",
    "workspace_id",
    "state",
    "risk_tier",
    "autonomy_tier",
]

COSA_INITIATIVE_RUNS_TOTAL = Counter(
    "cosa_initiative_runs_total",
    "Total AI initiative execution runs categorized by governance tiers and state.",
    labelnames=INITIATIVE_LABELS,
)

COSA_INITIATIVE_RUN_DURATION_SECONDS = Histogram(
    "cosa_initiative_run_duration_seconds",
    "Duration of AI initiative execution runs in seconds.",
    labelnames=INITIATIVE_LABELS,
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

COSA_INITIATIVE_GATE_EVALUATIONS_TOTAL = Counter(
    "cosa_initiative_gate_evaluations_total",
    "Total promotion gate evaluations executed for AI initiatives.",
    labelnames=[
        "initiative_id",
        "workspace_id",
        "gate_result",
        "risk_tier",
        "autonomy_tier",
    ],
)

COSA_INITIATIVE_ACTIVE_GAUGE = Gauge(
    "cosa_initiative_active",
    "Gauge indicating whether an AI initiative is currently active (1) or paused/retired (0).",
    labelnames=INITIATIVE_LABELS,
)


def record_initiative_run(
    *,
    initiative_id: str,
    workspace_id: str,
    state: str,
    risk_tier: str = "LOW",
    autonomy_tier: str = "A0",
    duration_sec: float | None = None,
) -> None:
    """Record an initiative execution outcome and optional latency."""
    labels = {
        "initiative_id": initiative_id,
        "workspace_id": workspace_id,
        "state": state,
        "risk_tier": risk_tier,
        "autonomy_tier": autonomy_tier,
    }
    COSA_INITIATIVE_RUNS_TOTAL.labels(**labels).inc()
    if duration_sec is not None and duration_sec >= 0:
        COSA_INITIATIVE_RUN_DURATION_SECONDS.labels(**labels).observe(duration_sec)


def record_initiative_gate_evaluation(
    *,
    initiative_id: str,
    workspace_id: str,
    gate_result: str,
    risk_tier: str = "LOW",
    autonomy_tier: str = "A0",
) -> None:
    """Record the result of a promotion gate evaluation."""
    COSA_INITIATIVE_GATE_EVALUATIONS_TOTAL.labels(
        initiative_id=initiative_id,
        workspace_id=workspace_id,
        gate_result=gate_result,
        risk_tier=risk_tier,
        autonomy_tier=autonomy_tier,
    ).inc()


def set_initiative_active_state(
    *,
    initiative_id: str,
    workspace_id: str,
    state: str,
    risk_tier: str = "LOW",
    autonomy_tier: str = "A0",
    active: bool = True,
) -> None:
    """Set the active status gauge for an initiative."""
    labels = {
        "initiative_id": initiative_id,
        "workspace_id": workspace_id,
        "state": state,
        "risk_tier": risk_tier,
        "autonomy_tier": autonomy_tier,
    }
    COSA_INITIATIVE_ACTIVE_GAUGE.labels(**labels).set(1 if active else 0)
