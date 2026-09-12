import pytest

from agent.workflows.approval_step import ApprovalGateStep
from agent.workflows.engine import WorkflowEngine
from agent.workflows.models import WorkflowStatus
from agent.workflows.steps import AgentStep, DeterministicStep


class _MockAgentResult:
    def __init__(self, status: str, output: str = "", error: str = ""):
        self.status = status
        self.output = output
        self.error = error


class _MockResearcherAgent:
    async def run(self, task):
        return _MockAgentResult(status="COMPLETED", output="Acme Corp is a mid-market SaaS company, 50 employees.")


from agent.capabilities.approval_service import DurableApprovalService
from agent.runs.repository import InMemoryRunRepository


class _MockPolicyEngine:
    def evaluate(self, p):
        return "REQUIRE_APPROVAL"


async def _business_write(state: dict) -> dict:
    return {"crm_record_id": "crm-42"}


async def _notify(state: dict) -> dict:
    return {"notified": True}


def _build_steps(approval_service: DurableApprovalService) -> list:
    researcher = _MockResearcherAgent()
    return [
        AgentStep("research", researcher, goal_key="goal", output_key="research_notes", agent_key="researcher"),
        ApprovalGateStep(
            "human-approval",
            policy_engine=_MockPolicyEngine(),
            approval_service=approval_service,
            action="create_crm_record",
            subject_key="goal",
            requester="researcher",
        ),
        DeterministicStep("business-write", _business_write),
        DeterministicStep("notify", _notify),
    ]


@pytest.mark.asyncio
async def test_full_workflow_completes_end_to_end_when_approved():
    repo = InMemoryRunRepository()
    approval_service = DurableApprovalService(repo)
    engine = WorkflowEngine()
    steps = _build_steps(approval_service)

    workflow = await engine.start(
        "prospect-research-flow", steps, {"goal": "research Acme Corp", "workspace_id": "ws1"}
    )
    assert workflow.status == WorkflowStatus.WAITING_APPROVAL
    assert workflow.state["research_notes"] == "Acme Corp is a mid-market SaaS company, 50 employees."

    await approval_service.submit_decision(
        approval_id=workflow.pending_approval_id, reviewer="founder", approved=True
    )
    resumed = await engine.resume(workflow, steps)

    assert resumed.status == WorkflowStatus.COMPLETED
    assert resumed.state["crm_record_id"] == "crm-42"
    assert resumed.state["notified"] is True


@pytest.mark.asyncio
async def test_full_workflow_stops_before_business_write_when_denied():
    repo = InMemoryRunRepository()
    approval_service = DurableApprovalService(repo)
    engine = WorkflowEngine()
    steps = _build_steps(approval_service)

    workflow = await engine.start(
        "prospect-research-flow", steps, {"goal": "research Acme Corp", "workspace_id": "ws1"}
    )
    await approval_service.submit_decision(
        approval_id=workflow.pending_approval_id, reviewer="founder", approved=False, reason="need more info"
    )
    resumed = await engine.resume(workflow, steps)

    assert resumed.status == WorkflowStatus.FAILED
    assert "crm_record_id" not in resumed.state
    assert "need more info" in resumed.error
