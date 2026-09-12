from __future__ import annotations

import pytest

from agent.workflows.engine import WorkflowEngine
from agent.workflows.models import StepStatus, WorkflowStatus
from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec


from types import SimpleNamespace


class MockGateway:
    def __init__(self, handlers: dict):
        self.handlers = handlers

    async def execute(self, request):
        h = self.handlers.get(request.capability_id)
        if not h:
            return SimpleNamespace(
                status="failed",
                error_message=f"No handler for {request.capability_id}",
                tool_call_id=getattr(request, "tool_call_id", "tc-1"),
            )
        try:
            res = await h(request.input_payload)
            return SimpleNamespace(
                status="completed",
                output_payload=res,
                tool_call_id=getattr(request, "tool_call_id", "tc-1"),
            )
        except Exception as exc:
            return SimpleNamespace(
                status="failed",
                error_message=str(exc),
                tool_call_id=getattr(request, "tool_call_id", "tc-1"),
            )


@pytest.mark.asyncio
async def test_workflow_step_on_failure_triggers_compensation():
    compensation_called = []

    async def step_fetch(args):
        return {"items": ["item1"]}

    async def step_failing_action(args):
        raise RuntimeError("Network timeout connecting to external API")

    async def step_compensate_handler(args):
        compensation_called.append(True)
        return {"compensated": True, "fallback_logged": True}

    gateway = MockGateway(
        {
            "fetch.data": step_fetch,
            "dangerous.action": step_failing_action,
            "compensate.fallback": step_compensate_handler,
        }
    )
    engine = WorkflowEngine(gateway=gateway)

    spec = WorkflowSpec(
        id="test.compensation",
        steps=[
            WorkflowStepSpec(id="step_fetch", type=StepType.TOOL_CALL, tool="fetch.data"),
            WorkflowStepSpec(
                id="step_action",
                type=StepType.TOOL_CALL,
                tool="dangerous.action",
                depends_on=["step_fetch"],
                on_failure="step_compensate",
            ),
            WorkflowStepSpec(
                id="step_compensate",
                type=StepType.TOOL_CALL,
                tool="compensate.fallback",
            ),
        ],
    )

    workflow = await engine.execute_spec(spec, initial_state={"workspace_id": "ws1"})

    assert workflow.status == WorkflowStatus.FAILED
    assert workflow.failed_step_name == "step_action"
    assert len(compensation_called) == 1
    assert workflow.state["_compensated_step"] == "step_action"
    assert workflow.state["step_compensate"] == {"compensated": True, "fallback_logged": True}
    assert workflow.step_outcomes["step_compensate"].status == StepStatus.COMPLETED
