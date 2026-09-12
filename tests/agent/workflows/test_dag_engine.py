from __future__ import annotations

import asyncio
import time
import pytest

from agent.workflows.engine import WorkflowEngine
from agent.workflows.models import WorkflowStatus
from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec


from types import SimpleNamespace


class MockGateway:
    def __init__(self, handlers: dict):
        self.handlers = handlers

    async def execute(self, request):
        h = self.handlers.get(request.capability_id)
        res = await h(request.input_payload) if h else {}
        return SimpleNamespace(
            status="completed",
            output_payload=res,
            tool_call_id=getattr(request, "tool_call_id", "tc-1"),
        )


@pytest.mark.asyncio
async def test_dag_sequential_execution_order():
    execution_order = []

    async def step1_handler(args):
        execution_order.append("fetch_evidence")
        return {"items": ["item1", "item2"]}

    async def step2_handler(args):
        execution_order.append("evaluate_gate")
        return {"gate_score": 95}

    async def step3_handler(args):
        execution_order.append("notify_founder")
        return {"status": "sent"}

    gateway = MockGateway(
        {
            "strategy.evidence.list": step1_handler,
            "strategy.gate_evaluation.create": step2_handler,
            "notification.send": step3_handler,
        }
    )
    engine = WorkflowEngine(gateway=gateway)

    spec = WorkflowSpec(
        id="test.sequential",
        steps=[
            WorkflowStepSpec(id="fetch_evidence", type=StepType.TOOL_CALL, tool="strategy.evidence.list"),
            WorkflowStepSpec(
                id="evaluate_gate",
                type=StepType.TOOL_CALL,
                tool="strategy.gate_evaluation.create",
                depends_on=["fetch_evidence"],
            ),
            WorkflowStepSpec(
                id="notify_founder",
                type=StepType.TOOL_CALL,
                tool="notification.send",
                depends_on=["evaluate_gate"],
            ),
        ],
    )

    workflow = await engine.execute_spec(spec, initial_state={"workspace_id": "ws1"})

    assert workflow.status == WorkflowStatus.COMPLETED
    assert execution_order == ["fetch_evidence", "evaluate_gate", "notify_founder"]
    assert workflow.state["fetch_evidence"] == {"items": ["item1", "item2"]}
    assert workflow.state["evaluate_gate"] == {"gate_score": 95}
    assert workflow.state["notify_founder"] == {"status": "sent"}


@pytest.mark.asyncio
async def test_dag_parallel_execution_timing():
    async def task_a_handler(args):
        await asyncio.sleep(0.08)
        return {"result_a": 1}

    async def task_b_handler(args):
        await asyncio.sleep(0.08)
        return {"result_b": 2}

    async def merge_handler(args):
        return {"merged": True}

    gateway = MockGateway(
        {
            "task.a": task_a_handler,
            "task.b": task_b_handler,
            "task.merge": merge_handler,
        }
    )
    engine = WorkflowEngine(gateway=gateway)

    spec = WorkflowSpec(
        id="test.parallel",
        steps=[
            WorkflowStepSpec(id="step_a", type=StepType.TOOL_CALL, tool="task.a"),
            WorkflowStepSpec(id="step_b", type=StepType.TOOL_CALL, tool="task.b"),
            WorkflowStepSpec(
                id="step_merge",
                type=StepType.TOOL_CALL,
                tool="task.merge",
                depends_on=["step_a", "step_b"],
            ),
        ],
    )

    start_time = time.perf_counter()
    workflow = await engine.execute_spec(spec, initial_state={})
    elapsed = time.perf_counter() - start_time

    assert workflow.status == WorkflowStatus.COMPLETED
    assert workflow.state["step_a"] == {"result_a": 1}
    assert workflow.state["step_b"] == {"result_b": 2}
    assert workflow.state["step_merge"] == {"merged": True}
    assert elapsed < 0.15


def test_application_has_no_legacy_coordination_imports() -> None:
    from pathlib import Path

    forbidden = (
        "agent.coordination.approval_gate",
        "agent.coordination.delegate",
        "agent.coordination.parallel",
        "agent.coordination.quality_gate",
        "agent.coordination.risk_classification",
        "agent.coordination.supervisor",
        "agent.coordination.synthesis",
    )
    text = "\n".join(
        path.read_text()
        for root in (Path("apps"), Path("packages"))
        for path in root.rglob("*.py")
        if "coordination" not in path.parts
    )
    assert not any(name in text for name in forbidden)

