# backend/app/workforce/agents/orchestration/adk/nodes/execution_node.py
"""Node cuối — finalize AgentRun/OutcomeRun/Outcome, y hệt đuôi
chief_of_staff.py::orchestrate (dòng ~747-754)."""
from datetime import datetime, timezone
from typing import Any

from agent_runtime.sessions.models import AgentRun
from google.adk.workflow._function_node import FunctionNode

from app.db.session import SessionLocal
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.workforce.agents.governance.quality_gate import QualityGateVerdict
from app.workforce.agents.governance.states import validate_run_transition


async def execution_finalize_fn(ctx: Any) -> dict[str, Any]:
    db = SessionLocal()
    try:
        return _finalize(ctx, db)
    finally:
        db.close()


def _finalize(ctx: Any, db) -> dict[str, Any]:
    mission_run = db.query(AgentRun).filter(AgentRun.id == ctx.state["mission_id"]).one()
    outcome = db.query(Outcome).filter(Outcome.id == ctx.state["outcome_id"]).one()
    outcome_run = db.query(OutcomeRun).filter(OutcomeRun.id == ctx.state["outcome_run_id"]).one()

    if ctx.state.get("governance_block_reason"):
        # Đến từ route "blocked" của GovernanceGateNode (Task 13) — budget/stuck
        # loop chặn mission TRƯỚC khi synthesis chạy, y hệt nhánh gov_failure
        # sớm trong chief_of_staff.py::orchestrate (KHÔNG có synthesis_status/
        # quality_gate_results để đọc).
        final_status = "failed"
    else:
        synthesis_status = ctx.state.get("synthesis_status", "partial")
        quality_gate_results: dict[str, Any] = ctx.state.get("quality_gate_results", {})
        any_gate_failed = any(
            (r.get("verdict") == QualityGateVerdict.FAIL.value or r.get("verdict") == QualityGateVerdict.FAIL)
            if isinstance(r, dict)
            else (getattr(r, "verdict", None) == QualityGateVerdict.FAIL)
            for r in quality_gate_results.values()
        )
        final_status = synthesis_status
        if any_gate_failed and final_status == "completed":
            final_status = "failed"

    mission_run.status = validate_run_transition(mission_run.status, final_status)
    mission_run.finished_at = datetime.now(timezone.utc)
    outcome_run.status = (
        "succeeded" if final_status == "completed"
        else ("failed" if final_status == "failed" else "running")
    )
    outcome_run.completed_at = datetime.now(timezone.utc)
    outcome.status = (
        "completed" if final_status == "completed"
        else ("failed" if final_status == "failed" else "planning")
    )
    db.commit()

    ctx.state["final_status"] = final_status
    return {"final_status": final_status}


def build_execution_node() -> FunctionNode:
    return FunctionNode(func=execution_finalize_fn, name="execution_node")
