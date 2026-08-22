# backend/agentos/evals/agent_eval.py
from __future__ import annotations

from pydantic import BaseModel

from agentos.core.models import AgentRun, AgentRunStatus
from agentos.observability.metrics import RunMetrics, compute_run_metrics


class AgentEvalResult(BaseModel):
    goal_completion: bool
    tool_calls_made: int
    latency_seconds: float
    human_acceptance: bool | None = None


def evaluate_agent_run(
    run: AgentRun, spans: list[dict], *, human_acceptance: bool | None = None
) -> AgentEvalResult:
    """Agent Eval (blueprint §52), the metrics achievable purely from
    Phase 0/1 data: goal completion (run status), tool_calls_made and
    latency (from RunMetrics), and human_acceptance as an optional
    caller-supplied signal (there's no feedback-collection mechanism yet
    to source it automatically — later hardening). Plan quality, tool
    accuracy, retry count, cost, and policy compliance need
    instrumentation this phase doesn't add (real ModelProvider usage
    tracking, a Planner that produces gradeable multi-step plans,
    GovernanceKernel wiring) — deliberately out of scope here.
    """
    metrics: RunMetrics = compute_run_metrics(run, spans)
    return AgentEvalResult(
        goal_completion=run.status == AgentRunStatus.COMPLETED,
        tool_calls_made=metrics.tool_call_count,
        latency_seconds=metrics.latency_seconds,
        human_acceptance=human_acceptance,
    )
