from __future__ import annotations

import pytest

from agent.workflows.definition_registry import WorkflowDefinitionRegistry
from agent.workflows.engine import WorkflowEngine
from agent.workflows.models import WorkflowStatus
from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec
from agent.workflows.approval_step import ApprovalGateStep
from agent.workflows.steps import DeterministicStep



@pytest.mark.asyncio
async def test_case_a_workflow_spec_drift():
    """Case A: Workflow spec drift (Master Guide §41.1 Case A).
    
    Kịch bản:
    1. Workflow v1 có steps: [step_1, approval_gate, step_2_v1].
    2. Run khởi chạy v1, hoàn thành step_1, pause ở approval_gate (checkpoint ghi nhận pinned version 1 + definition hash).
    3. Trong lúc đang pause, Workflow v2 được xuất bản: [step_1, approval_gate, step_2_v2_drifted, step_3_new_node].
    4. Reviewer phê duyệt, Run resume lại.
    5. Invariant: Run resumed BẮT BUỘC thực thi v1, KHÔNG ĐƯỢC chạy step_2_v2_drifted hay step_3_new_node.
    """
    registry = WorkflowDefinitionRegistry()
    engine = WorkflowEngine()

    executions = []

    # Định nghĩa v1
    spec_v1 = WorkflowSpec(
        id="financial_flow",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(id="step_1", type=StepType.DETERMINISTIC),
            WorkflowStepSpec(id="approval_gate", type=StepType.APPROVAL_GATE, depends_on=["step_1"]),
            WorkflowStepSpec(id="step_2_v1", type=StepType.DETERMINISTIC, depends_on=["approval_gate"]),

        ],
    )
    v1_record = registry.register_version(spec_v1)
    assert v1_record.version_no == 1

    # Handlers cho v1
    async def step1_fn(state):
        executions.append("step_1_v1")
        return {"data_v1": True}

    async def step2_v1_fn(state):
        executions.append("step_2_v1")
        return {"result": "v1_completed"}

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
        def __init__(self):
            self.allow = False

        def evaluate(self, p):
            return "ALLOW" if self.allow else "REQUIRE_APPROVAL"

    mock_policy = _MockPolicyEngine()
    mock_approval = _MockApprovalService()

    custom_builders_v1 = {
        "step_1": lambda s: DeterministicStep("step_1", step1_fn),
        "approval_gate": lambda s: ApprovalGateStep(
            "approval_gate",
            policy_engine=mock_policy,
            approval_service=mock_approval,
        ),
        "step_2_v1": lambda s: DeterministicStep("step_2_v1", step2_v1_fn),
    }


    # 1. Khởi chạy v1 -> pause ở approval_gate
    wf = await engine.execute_spec(
        spec_v1,
        initial_state={},
        custom_step_builders=custom_builders_v1,
    )
    assert wf.status == WorkflowStatus.WAITING_APPROVAL
    assert "step_1" in wf.completed_steps
    assert executions == ["step_1_v1"]

    # 2. Xuất bản v2 với các node hoàn toàn mới
    spec_v2 = WorkflowSpec(
        id="financial_flow",
        version="2.0.0",
        steps=[
            WorkflowStepSpec(id="step_1", type=StepType.DETERMINISTIC),
            WorkflowStepSpec(id="approval_gate", type=StepType.APPROVAL_GATE, depends_on=["step_1"]),
            WorkflowStepSpec(id="step_2_v2_drifted", type=StepType.DETERMINISTIC, depends_on=["approval_gate"]),
            WorkflowStepSpec(id="step_3_new_node", type=StepType.DETERMINISTIC, depends_on=["step_2_v2_drifted"]),
        ],
    )
    v2_record = registry.register_version(spec_v2)
    assert v2_record.version_no == 2
    assert registry.current_version("financial_flow").version_no == 2


    # 3. Reviewer phê duyệt và Resume Run theo đúng spec_v1 gốc đã pin
    mock_approval.decide("appr-1", reviewer="finance_lead", approved=True)
    mock_policy.allow = True
    wf.completed_steps.append("approval_gate")
    wf.status = WorkflowStatus.RUNNING

    wf_resumed = await engine.execute_spec(
        spec_v1,
        initial_state={},
        workflow=wf,
        custom_step_builders=custom_builders_v1,
    )

    # 4. Invariant: Run hoàn tất đúng spec v1 gốc
    assert wf_resumed.status == WorkflowStatus.COMPLETED
    assert "step_2_v1" in wf_resumed.completed_steps
    assert "step_2_v2_drifted" not in wf_resumed.completed_steps
    assert "step_3_new_node" not in wf_resumed.completed_steps
    assert executions == ["step_1_v1", "step_2_v1"]


