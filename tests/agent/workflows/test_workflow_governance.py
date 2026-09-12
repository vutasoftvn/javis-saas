from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from agent.capabilities.approval_service import DurableApprovalService
from agent.runs.repository import InMemoryRunRepository
from agent.workflows.engine import WorkflowEngine
from agent.workflows.models import WorkflowStatus
from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec
from agent.workflows.tool_step import GatewayToolCallStep


class MockGateway:
    def __init__(self, outcome_status: str = "completed", output: Any = None) -> None:
        self.outcome_status = outcome_status
        self.output = output or {"result": "success"}
        self.executed_requests: list[Any] = []

    async def execute(self, request: Any) -> Any:
        self.executed_requests.append(request)
        if self.outcome_status == "waiting_approval":
            return SimpleNamespace(
                status="waiting_approval",
                wait_descriptor=SimpleNamespace(related_ref="appr-gw-123"),
                tool_call_id=getattr(request, "tool_call_id", "tc-1"),
            )
        if self.outcome_status in ("denied", "failed"):
            return SimpleNamespace(
                status=self.outcome_status,
                error_message=f"Gateway execution {self.outcome_status}",
                tool_call_id=getattr(request, "tool_call_id", "tc-1"),
            )
        return SimpleNamespace(
            status="completed",
            output_payload=self.output,
            tool_call_id=getattr(request, "tool_call_id", "tc-1"),
        )


@pytest.mark.asyncio
async def test_engine_refuses_tool_call_without_gateway() -> None:
    engine = WorkflowEngine(tool_registry=object())
    spec = WorkflowSpec(
        id="tool-flow",
        steps=[WorkflowStepSpec(id="step1", type=StepType.TOOL_CALL, tool="ops.write")],
    )
    with pytest.raises(RuntimeError, match="CapabilityGateway is required"):
        engine.build_steps_from_spec(spec)


@pytest.mark.asyncio
async def test_engine_compiles_tool_call_with_gateway() -> None:
    gateway = MockGateway()
    engine = WorkflowEngine(gateway=gateway)
    spec = WorkflowSpec(
        id="tool-flow",
        steps=[WorkflowStepSpec(id="step1", type=StepType.TOOL_CALL, tool="ops.write")],
    )
    steps = engine.build_steps_from_spec(spec)
    assert len(steps) == 1
    assert isinstance(steps[0], GatewayToolCallStep)
    assert steps[0].tool_name == "ops.write"


@pytest.mark.asyncio
async def test_workflow_engine_executes_tool_call_via_gateway() -> None:
    gateway = MockGateway(outcome_status="completed", output={"data": 42})
    engine = WorkflowEngine(gateway=gateway)
    spec = WorkflowSpec(
        id="tool-flow",
        steps=[WorkflowStepSpec(id="step1", type=StepType.TOOL_CALL, tool="ops.read")],
    )
    wf = await engine.execute_spec(spec, initial_state={"workspace_id": "ws-1"})
    assert wf.status == WorkflowStatus.COMPLETED
    assert wf.state["step1"] == {"data": 42}
    assert len(gateway.executed_requests) == 1
    assert gateway.executed_requests[0].capability_id == "ops.read"


@pytest.mark.asyncio
async def test_workflow_engine_pauses_when_gateway_returns_waiting_approval() -> None:
    gateway = MockGateway(outcome_status="waiting_approval")
    engine = WorkflowEngine(gateway=gateway)
    spec = WorkflowSpec(
        id="tool-flow",
        steps=[WorkflowStepSpec(id="deploy", type=StepType.TOOL_CALL, tool="ops.deploy")],
    )
    wf = await engine.execute_spec(spec, initial_state={"workspace_id": "ws-1"})
    assert wf.status == WorkflowStatus.WAITING_APPROVAL
    assert wf.pending_approval_id == "appr-gw-123"


@pytest.mark.asyncio
async def test_workflow_engine_fails_when_gateway_fails() -> None:
    gateway = MockGateway(outcome_status="denied")
    engine = WorkflowEngine(gateway=gateway)
    spec = WorkflowSpec(
        id="tool-flow",
        steps=[WorkflowStepSpec(id="del", type=StepType.TOOL_CALL, tool="ops.delete")],
    )
    wf = await engine.execute_spec(spec, initial_state={"workspace_id": "ws-1"})
    assert wf.status == WorkflowStatus.FAILED
    assert "denied" in wf.error.lower()


@pytest.mark.asyncio
async def test_workflow_engine_approval_gate_resumes_when_approved() -> None:
    repo = InMemoryRunRepository()
    approval_svc = DurableApprovalService(repo)
    gateway = MockGateway()
    engine = WorkflowEngine(gateway=gateway, approval_service=approval_svc)

    spec = WorkflowSpec(
        id="gate-flow",
        steps=[
            WorkflowStepSpec(
                id="gate",
                type=StepType.APPROVAL_GATE,
                action="publish_report",
                subject_key="report_ref",
            ),
            WorkflowStepSpec(
                id="done",
                type=StepType.DETERMINISTIC,
                depends_on=["gate"],
            ),
        ],
    )

    wf = await engine.execute_spec(
        spec,
        initial_state={"workspace_id": "ws-1", "report_ref": "rep-99"},
    )
    assert wf.status == WorkflowStatus.WAITING_APPROVAL
    assert wf.pending_approval_id is not None

    # Resume while still pending -> should stay WAITING_APPROVAL
    wf2 = await engine.resume_spec(wf, spec)
    assert wf2.status == WorkflowStatus.WAITING_APPROVAL

    # Approve
    await approval_svc.submit_decision(
        approval_id=wf.pending_approval_id,
        reviewer="founder",
        approved=True,
    )

    wf_resumed = await engine.resume_spec(wf, spec)
    assert wf_resumed.status == WorkflowStatus.COMPLETED
