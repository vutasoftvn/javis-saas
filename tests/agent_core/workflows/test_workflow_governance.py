from __future__ import annotations

import pytest

from agent_core.governance.contracts import AutonomyLevel, CapabilityRisk, DataScope
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.workflows.engine import WorkflowEngine
from agent_core.workflows.models import WorkflowStatus
from agent_core.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec
from agent_core.workflows.tool_step import ToolCallStep


class MockTool:
    def __init__(self, name: str, handler, risk=CapabilityRisk.LOW, permission="scoped_write"):
        self.name = name
        self.risk_level = risk
        self.permission = permission
        self._handler = handler

    async def execute(self, **kwargs):
        return await self._handler(kwargs)


class MockToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, tool):
        self._tools[tool.name] = tool

    def get(self, name: str):
        return self._tools.get(name)


class MockApproval:
    def __init__(self, id: str, action: str, run_id: str | None = None):
        self.id = id
        self.action = action
        self.run_id = run_id
        self.status = "PENDING"
        self.reason = ""


class MockApprovalService:
    def __init__(self):
        self._approvals = {}

    def request_approval(self, action: str, subject: str = "", requester: str = "", run_id: str | None = None, workspace_id: str | None = None):
        appr_id = f"appr-{len(self._approvals)+1}"
        appr = MockApproval(appr_id, action, run_id)
        self._approvals[appr_id] = appr
        return appr

    def get(self, approval_id: str):
        return self._approvals.get(approval_id)

    def find_by_run_and_action(self, run_id: str, action: str):
        for appr in self._approvals.values():
            if appr.run_id == run_id and appr.action == action:
                return appr
        return None

    def decide(self, approval_id: str, reviewer: str, approved: bool, reason: str = ""):
        if approval_id in self._approvals:
            self._approvals[approval_id].status = "APPROVED" if approved else "DENIED"
            self._approvals[approval_id].reason = reason


class MockPolicyEngine:
    def __init__(self, default_decision="ALLOW"):
        self.default_decision = default_decision

    def evaluate_access(self, role="founder", agent_permission_level=AutonomyLevel.L3_AUTONOMOUS, tool_risk_level=CapabilityRisk.LOW, tool_permission="scoped_write", **kwargs):
        if role == "viewer" and "admin_write" in str(tool_permission):
            return "DENY"
        if kwargs.get("data_scope") == DataScope.READ_ONLY and "write" in str(tool_permission):
            return "DENY"
        return self.default_decision


@pytest.mark.asyncio
async def test_tool_call_step_denied_by_policy():
    async def restricted_handler(args):
        return {"done": True}

    registry = MockToolRegistry()
    registry.register(
        MockTool(
            name="system.shutdown",
            handler=restricted_handler,
            risk=CapabilityRisk.CRITICAL,
            permission="admin_write",
        )
    )

    policy_engine = MockPolicyEngine()
    step = ToolCallStep(
        name="step_shutdown",
        tool_name="system.shutdown",
        tool_registry=registry,
        policy_engine=policy_engine,
        role="viewer",
        autonomy_level=AutonomyLevel.L1,
    )

    outcome = await step.run({"workspace_id": "ws1"})
    assert outcome.status.value == "FAILED"
    assert "denied by policy" in outcome.error.lower()


@pytest.mark.asyncio
async def test_tool_call_step_denied_by_data_scope_read_only():
    async def write_handler(args):
        return {"written": True}

    registry = MockToolRegistry()
    registry.register(
        MockTool(
            name="strategy.gate_evaluation.create",
            handler=write_handler,
            risk=CapabilityRisk.LOW,
            permission="scoped_write",
        )
    )

    policy_engine = MockPolicyEngine()
    step = ToolCallStep(
        name="step_write",
        tool_name="strategy.gate_evaluation.create",
        tool_registry=registry,
        policy_engine=policy_engine,
        role="founder",
        autonomy_level=AutonomyLevel.L3_AUTONOMOUS,
    )

    outcome = await step.run({"workspace_id": "ws1", "data_scope": DataScope.READ_ONLY})
    assert outcome.status.value == "FAILED"
    assert "denied by policy" in outcome.error.lower()


@pytest.mark.asyncio
async def test_tool_call_step_in_workflow_requires_approval():
    async def deploy_handler(args):
        return {"deployed": True}

    registry = MockToolRegistry()
    registry.register(
        MockTool(
            name="ops.deploy.prod",
            handler=deploy_handler,
            risk=CapabilityRisk.HIGH,
            permission="admin_write",
        )
    )

    policy_engine = MockPolicyEngine(default_decision="REQUIRE_APPROVAL")
    approval_svc = MockApprovalService()
    engine = WorkflowEngine(
        tool_registry=registry, policy_engine=policy_engine, approval_service=approval_svc
    )

    spec = WorkflowSpec(
        id="deploy-flow", steps=[WorkflowStepSpec(id="deploy", type=StepType.TOOL_CALL, tool="ops.deploy.prod")]
    )

    workflow = await engine.execute_spec(spec, initial_state={"workspace_id": "ws1", "run_id": "run-test-appr"})
    assert workflow.status == WorkflowStatus.WAITING_APPROVAL
    assert workflow.pending_approval_id is not None

    approval_svc.decide(workflow.pending_approval_id, reviewer="founder-1", approved=True)
    resumed = await engine.resume_spec(workflow, spec)

    assert resumed.status == WorkflowStatus.COMPLETED
    assert resumed.state["deploy"] == {"deployed": True}


@pytest.mark.asyncio
async def test_tool_call_step_does_not_silently_allow_after_policy_relaxes_mid_pause():
    async def deploy_handler(args):
        return {"deployed": True}

    registry = MockToolRegistry()
    registry.register(MockTool(name="ops.deploy.prod", handler=deploy_handler, risk=CapabilityRisk.HIGH, permission="admin_write"))

    policy_engine = MockPolicyEngine(default_decision="REQUIRE_APPROVAL")
    approval_svc = MockApprovalService()
    gov_store = InMemoryGovernanceStateStore()

    engine = WorkflowEngine(
        tool_registry=registry,
        policy_engine=policy_engine,
        approval_service=approval_svc,
        governance_store=gov_store,
    )

    spec = WorkflowSpec(
        id="deploy-flow", steps=[WorkflowStepSpec(id="deploy", type=StepType.TOOL_CALL, tool="ops.deploy.prod")]
    )

    workflow = await engine.execute_spec(spec, initial_state={"workspace_id": "ws1", "run_id": "run-relax"})
    assert workflow.status == WorkflowStatus.WAITING_APPROVAL

    # Giả lập policy nới lỏng sang ALLOW
    policy_engine.default_decision = "ALLOW"

    # Resume mà CHƯA có approval -> phải tiếp tục WAITING_APPROVAL hoặc FAILED
    resumed = await engine.resume_spec(workflow, spec)
    assert resumed.status == WorkflowStatus.WAITING_APPROVAL


@pytest.mark.asyncio
async def test_tool_call_step_without_a_run_id_skips_accumulation_and_behaves_as_before():
    async def echo_handler(args):
        return {"out": "ok"}

    registry = MockToolRegistry()
    registry.register(MockTool(name="test.echo", handler=echo_handler))

    step = ToolCallStep(name="echo", tool_name="test.echo", tool_registry=registry)
    outcome = await step.run({"workspace_id": "ws1"})
    assert outcome.status.value == "COMPLETED"
    assert outcome.updates == {"echo": {"out": "ok"}}


@pytest.mark.asyncio
async def test_workflow_engine_shares_governance_state_across_execute_spec_calls_on_the_same_engine():
    async def write_handler(args):
        return {"w": 1}

    registry = MockToolRegistry()
    registry.register(MockTool(name="ops.write", handler=write_handler, permission="scoped_write"))

    gov_store = InMemoryGovernanceStateStore()
    engine = WorkflowEngine(tool_registry=registry, governance_store=gov_store)

    spec = WorkflowSpec(id="w-flow", steps=[WorkflowStepSpec(id="step1", type=StepType.TOOL_CALL, tool="ops.write")])
    wf = await engine.execute_spec(spec, initial_state={"run_id": "run-shared"})
    assert wf.status == WorkflowStatus.COMPLETED

    saved = await gov_store.load_governance_state("run-shared", "run-shared:ops.write")
    assert saved is not None
    assert saved.accumulated.outcome.value == "ALLOW"

