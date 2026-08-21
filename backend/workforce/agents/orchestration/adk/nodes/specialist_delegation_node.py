# backend/app/workforce/agents/orchestration/adk/nodes/specialist_delegation_node.py
"""Mỗi domain (Sales/Finance/Marketing/Legal) là 1 FunctionNode riêng — tạo
RunStep + gọi TaskBoardService.assign_step() rồi PAUSE bằng RequestInput. KHÔNG
tự chạy DeepSeekHarnessAdapter trong tiến trình ADK — delegation-worker (process
riêng, backend/app/workforce/agents/delegation/worker.py) xử lý việc thật, và
MissionResumeJobService (Task 17-18) sẽ resume node này khi RunStep hoàn tất."""
from collections.abc import AsyncGenerator, Callable
from typing import Any

from google.adk.events.request_input import RequestInput
from google.adk.workflow._function_node import FunctionNode

from db.session import SessionLocal
from founder_os.outcomes.models import OutcomeRun
from workforce.agents.orchestration.adk.specialist_delegation import queue_specialist_delegation
from workforce.agents.orchestration.specialist_registry import SPECIALIST_REGISTRY


def interrupt_id_for_step(step_id: int) -> str:
    return f"delegation_step:{step_id}"


def build_specialist_delegation_fn(domain: str) -> Callable[[Any], AsyncGenerator[Any, None]]:
    async def specialist_delegation_fn(ctx: Any) -> AsyncGenerator[Any, None]:
        active_domains = ctx.state.get("active_domains", [])
        if active_domains and domain not in active_domains:
            yield {"skipped": True, "domain": domain}
            return

        spec = SPECIALIST_REGISTRY[domain]
        workspace_id = ctx.state["workspace_id"]
        runtime_name = ctx.state.get("specialist_runtime_name", "deepseek_harness")

        db = SessionLocal()
        try:
            outcome_run_id = ctx.state.get("outcome_run_id")
            if outcome_run_id is not None:
                outcome_run = db.query(OutcomeRun).filter(OutcomeRun.id == outcome_run_id).one()
            else:
                outcome_run = ctx.state["outcome_run"]
            step = await queue_specialist_delegation(
                db,
                workspace_id=workspace_id,
                outcome_run=outcome_run,
                domain=domain,
                spec=spec,
                runtime_name=runtime_name,
            )
            step_id = step.id
        finally:
            db.close()

        ctx.state.setdefault("specialist_step_ids", {})[domain] = step_id

        yield RequestInput(
            interrupt_id=interrupt_id_for_step(step_id),
            message=f"Waiting for {domain} specialist RunStep {step_id} to complete",
            response_schema=dict,
        )

    specialist_delegation_fn.__name__ = f"specialist_delegation_{domain}_fn"
    return specialist_delegation_fn


def build_specialist_delegation_node(domain: str) -> FunctionNode:
    fn = build_specialist_delegation_fn(domain)
    return FunctionNode(func=fn, name=f"specialist_delegation_{domain}_node", rerun_on_resume=False)
