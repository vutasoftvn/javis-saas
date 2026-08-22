import pytest

from agentos.core.approval import ApprovalService
from agentos.core.policy import PermissionClass, PolicyEngine
from agentos.workflows.approval_step import ApprovalGateStep
from agentos.workflows.engine import WorkflowEngine
from agentos.workflows.models import WorkflowStatus
from agentos.workflows.steps import DeterministicStep


async def _write_record(state: dict) -> dict:
    return {"record_id": "rec-123"}


async def _notify(state: dict) -> dict:
    return {"notified": True}


async def _failing_step(state: dict) -> dict:
    raise RuntimeError("should not run")


@pytest.mark.asyncio
async def test_workflow_completes_when_all_deterministic_steps_succeed():
    engine = WorkflowEngine()
    steps = [DeterministicStep("write", _write_record), DeterministicStep("notify", _notify)]

    workflow = await engine.start("business-write-flow", steps, {})

    assert workflow.status == WorkflowStatus.COMPLETED
    assert workflow.state == {"record_id": "rec-123", "notified": True}
    assert workflow.had_approval_gate is False
    assert workflow.failed_step_name is None


@pytest.mark.asyncio
async def test_workflow_pauses_at_approval_gate_and_resumes_when_approved():
    approval_service = ApprovalService()
    engine = WorkflowEngine()
    gate = ApprovalGateStep(
        "approve-send",
        policy_engine=PolicyEngine(),
        approval_service=approval_service,
        permission=PermissionClass.SEND_MESSAGE,
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )
    steps = [DeterministicStep("write", _write_record), gate, DeterministicStep("notify", _notify)]

    workflow = await engine.start("send-flow", steps, {"campaign_id": "camp-1"})
    assert workflow.status == WorkflowStatus.WAITING_APPROVAL
    assert workflow.pending_approval_id is not None
    assert workflow.had_approval_gate is True

    approval_service.decide(workflow.pending_approval_id, reviewer="founder", approved=True)
    resumed = await engine.resume(workflow, steps)

    assert resumed.status == WorkflowStatus.COMPLETED
    assert resumed.state["notified"] is True
    assert resumed.had_approval_gate is True


@pytest.mark.asyncio
async def test_workflow_fails_when_resumed_approval_is_denied():
    approval_service = ApprovalService()
    engine = WorkflowEngine()
    gate = ApprovalGateStep(
        "approve-send",
        policy_engine=PolicyEngine(),
        approval_service=approval_service,
        permission=PermissionClass.SEND_MESSAGE,
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )
    steps = [gate, DeterministicStep("notify", _failing_step)]

    workflow = await engine.start("send-flow", steps, {"campaign_id": "camp-1"})
    approval_service.decide(workflow.pending_approval_id, reviewer="founder", approved=False, reason="not ready")
    resumed = await engine.resume(workflow, steps)

    assert resumed.status == WorkflowStatus.FAILED
    assert "not ready" in resumed.error
    assert resumed.failed_step_name == "approve-send"


@pytest.mark.asyncio
async def test_resume_is_a_noop_when_not_waiting_approval():
    engine = WorkflowEngine()
    steps = [DeterministicStep("write", _write_record)]
    workflow = await engine.start("flow", steps, {})

    resumed = await engine.resume(workflow, steps)

    assert resumed is workflow
