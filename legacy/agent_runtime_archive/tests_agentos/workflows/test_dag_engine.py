from __future__ import annotations

import asyncio
import time
import pytest

from agentos.tools.registry import ToolRegistry, ToolSpec
from agentos.workflows.engine import WorkflowEngine
from agentos.workflows.models import WorkflowStatus
from agentos.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec


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

    registry = ToolRegistry()
    registry.register(ToolSpec(name="strategy.evidence.list", description="d", handler=step1_handler))
    registry.register(ToolSpec(name="strategy.gate_evaluation.create", description="d", handler=step2_handler))
    registry.register(ToolSpec(name="notification.send", description="d", handler=step3_handler))

    engine = WorkflowEngine(tool_registry=registry)

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

    registry = ToolRegistry()
    registry.register(ToolSpec(name="task.a", description="d", handler=task_a_handler))
    registry.register(ToolSpec(name="task.b", description="d", handler=task_b_handler))
    registry.register(ToolSpec(name="task.merge", description="d", handler=merge_handler))

    engine = WorkflowEngine(tool_registry=registry)

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

    # Parallel execution of two 0.08s tasks should complete in < 0.14s (much less than 0.16s sequential)
    assert elapsed < 0.14, f"Parallel execution took {elapsed:.3f}s, expected < 0.14s"
