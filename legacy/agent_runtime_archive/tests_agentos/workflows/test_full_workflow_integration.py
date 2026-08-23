import pytest

from agentos.core.model_provider import ModelResponse, StubModelProvider
from agentos.core.approval import ApprovalService
from agentos.core.policy import PermissionClass, PolicyEngine
from agentos.core.runtime import AgentRuntime
from agentos.tools.registry import ToolRegistry
from agentos.workflows.approval_step import ApprovalGateStep
from agentos.workflows.engine import WorkflowEngine
from agentos.workflows.models import WorkflowStatus
from agentos.workflows.steps import AgentStep, DeterministicStep


async def _business_write(state: dict) -> dict:
    return {"crm_record_id": "crm-42"}


async def _notify(state: dict) -> dict:
    return {"notified": True}


def _build_steps(approval_service: ApprovalService) -> list:
    researcher = AgentRuntime(
        StubModelProvider([ModelResponse(text="Acme Corp is a mid-market SaaS company, 50 employees.")]),
        ToolRegistry(),
    )
    return [
        AgentStep("research", researcher, goal_key="goal", output_key="research_notes", agent_key="researcher"),
        ApprovalGateStep(
            "human-approval",
            policy_engine=PolicyEngine(),
            approval_service=approval_service,
            permission=PermissionClass.MODIFY_BUSINESS_DATA,
            action="create_crm_record",
            subject_key="goal",
            requester="researcher",
        ),
        DeterministicStep("business-write", _business_write),
        DeterministicStep("notify", _notify),
    ]


@pytest.mark.asyncio
async def test_full_workflow_completes_end_to_end_when_approved():
    approval_service = ApprovalService()
    engine = WorkflowEngine()
    steps = _build_steps(approval_service)

    workflow = await engine.start(
        "prospect-research-flow", steps, {"goal": "research Acme Corp", "workspace_id": "ws1"}
    )
    assert workflow.status == WorkflowStatus.WAITING_APPROVAL
    assert workflow.state["research_notes"] == "Acme Corp is a mid-market SaaS company, 50 employees."

    approval_service.decide(workflow.pending_approval_id, reviewer="founder", approved=True)
    resumed = await engine.resume(workflow, steps)

    assert resumed.status == WorkflowStatus.COMPLETED
    assert resumed.state["crm_record_id"] == "crm-42"
    assert resumed.state["notified"] is True


@pytest.mark.asyncio
async def test_full_workflow_stops_before_business_write_when_denied():
    approval_service = ApprovalService()
    engine = WorkflowEngine()
    steps = _build_steps(approval_service)

    workflow = await engine.start(
        "prospect-research-flow", steps, {"goal": "research Acme Corp", "workspace_id": "ws1"}
    )
    approval_service.decide(
        workflow.pending_approval_id, reviewer="founder", approved=False, reason="need more info"
    )
    resumed = await engine.resume(workflow, steps)

    assert resumed.status == WorkflowStatus.FAILED
    assert "crm_record_id" not in resumed.state
    assert "need more info" in resumed.error
