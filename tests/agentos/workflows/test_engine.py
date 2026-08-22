import pytest

from agentos.core.approval import ApprovalService
from agentos.core.policy import PermissionClass, PolicyEngine
from agentos.workflows.approval_step import ApprovalGateStep
from agentos.workflows.engine import WorkflowEngine
from agentos.workflows.models import StepOutcome, StepStatus, WorkflowStatus
from agentos.workflows.steps import CompensatingStep, DeterministicStep


class _BoomStep:
    """Step luôn FAILED — dùng để giả lập 1 step sau đó trong workflow bị
    lỗi thật (không phải exception văng ra ngoài, mà là StepOutcome.FAILED
    đúng convention của WorkflowStep.run()).
    """

    name = "boom"

    async def run(self, state: dict) -> StepOutcome:
        return StepOutcome(status=StepStatus.FAILED, error="downstream step exploded")


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


@pytest.mark.asyncio
async def test_failed_step_triggers_compensation_of_earlier_completed_steps_in_reverse_order():
    order: list[str] = []

    async def _compensate_write(state: dict) -> None:
        order.append("compensate-write")

    async def _compensate_charge(state: dict) -> None:
        order.append("compensate-charge")

    async def _charge(state: dict) -> dict:
        return {"charged": True}

    engine = WorkflowEngine()
    steps = [
        CompensatingStep(DeterministicStep("write", _write_record), compensate=_compensate_write),
        CompensatingStep(DeterministicStep("charge", _charge), compensate=_compensate_charge),
        _BoomStep(),
    ]

    workflow = await engine.start("compensating-flow", steps, {})

    assert workflow.status == WorkflowStatus.FAILED
    assert workflow.failed_step_name == "boom"
    # Bù trừ theo thứ tự ngược lại thứ tự hoàn thành: charge trước, write sau.
    assert order == ["compensate-charge", "compensate-write"]


@pytest.mark.asyncio
async def test_compensation_error_is_recorded_but_does_not_block_other_rollbacks():
    order: list[str] = []

    async def _compensate_ok(state: dict) -> None:
        order.append("compensate-ok")

    async def _compensate_broken(state: dict) -> None:
        raise RuntimeError("rollback bug")

    engine = WorkflowEngine()
    steps = [
        CompensatingStep(DeterministicStep("first", _write_record), compensate=_compensate_ok),
        CompensatingStep(DeterministicStep("second", _write_record), compensate=_compensate_broken),
        _BoomStep(),
    ]

    workflow = await engine.start("compensating-flow-with-error", steps, {})

    assert workflow.status == WorkflowStatus.FAILED
    # compensate của "second" lỗi nhưng compensate của "first" vẫn phải chạy.
    assert order == ["compensate-ok"]
    assert "second" in workflow.state["_compensation_errors"][0]


@pytest.mark.asyncio
async def test_compensation_runs_when_a_resumed_approval_is_denied():
    order: list[str] = []

    async def _compensate_write(state: dict) -> None:
        order.append("compensate-write")

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
    steps = [CompensatingStep(DeterministicStep("write", _write_record), compensate=_compensate_write), gate]

    workflow = await engine.start("send-flow-with-compensation", steps, {"campaign_id": "camp-1"})
    approval_service.decide(workflow.pending_approval_id, reviewer="founder", approved=False, reason="not ready")
    resumed = await engine.resume(workflow, steps)

    assert resumed.status == WorkflowStatus.FAILED
    assert order == ["compensate-write"]
