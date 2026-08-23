import pytest

from agent_core.workflows.approval_step import ApprovalGateStep
from agent_core.workflows.engine import WorkflowEngine
from agent_core.workflows.models import WorkflowStatus
from agent_core.workflows.steps import AgentStep, DeterministicStep


class _MockAgentResult:
    def __init__(self, status: str, output: str = "", error: str = ""):
        self.status = status
        self.output = output
        self.error = error


class _MockResearcherAgent:
    async def run(self, task):
        return _MockAgentResult(status="COMPLETED", output="Acme Corp is a mid-market SaaS company, 50 employees.")


class _MockApproval:
    def __init__(self, id: str):
        self.id = id
        self.status = "PENDING"
        self.reason = ""


class _MockApprovalService:
    def __init__(self):
        self._approvals = {}

    def request_approval(self, **kw):
        appr = _MockApproval("appr-1")
        self._approvals["appr-1"] = appr
        return appr

    def get(self, approval_id: str):
        return self._approvals.get(approval_id)

    def decide(self, approval_id: str, reviewer: str, approved: bool, reason: str = ""):
        if approval_id in self._approvals:
            self._approvals[approval_id].status = "APPROVED" if approved else "DENIED"
            self._approvals[approval_id].reason = reason


class _MockPolicyEngine:
    def evaluate(self, p):
        return "REQUIRE_APPROVAL"


async def _business_write(state: dict) -> dict:
    return {"crm_record_id": "crm-42"}


async def _notify(state: dict) -> dict:
    return {"notified": True}


def _build_steps(approval_service: _MockApprovalService) -> list:
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
    approval_service = _MockApprovalService()
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
    approval_service = _MockApprovalService()
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
