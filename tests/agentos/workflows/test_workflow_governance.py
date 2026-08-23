from __future__ import annotations

import pytest

from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agentos.core.approval import ApprovalService
from agentos.core.policy import DataScope, PermissionLevel, PolicyEngine, ToolPermission, ToolRiskLevel
from agentos.tools.registry import ToolRegistry
from agentos.tools.spec import ToolSpecV2
from agentos.workflows.engine import WorkflowEngine
from agentos.workflows.models import WorkflowStatus
from agentos.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec
from agentos.workflows.tool_step import ToolCallStep


@pytest.mark.asyncio
async def test_tool_call_step_denied_by_policy():
    async def restricted_handler(args):
        return {"done": True}

    registry = ToolRegistry()
    registry.register(
        ToolSpecV2(
            name="system.shutdown",
            description="Shutdown system",
            handler=restricted_handler,
            risk_level=ToolRiskLevel.CRITICAL,
            tool_permission=ToolPermission.ADMIN_WRITE,
        )
    )

    # Viewer role with L1_SUGGEST permission cannot execute ADMIN_WRITE
    policy_engine = PolicyEngine()
    step = ToolCallStep(
        name="step_shutdown",
        tool_name="system.shutdown",
        tool_registry=registry,
        policy_engine=policy_engine,
        role="viewer",
        agent_permission_level=PermissionLevel.L1_SUGGEST,
    )

    outcome = await step.run({"workspace_id": "ws1"})
    assert outcome.status.value == "FAILED"
    assert "denied by policy" in outcome.error.lower()


@pytest.mark.asyncio
async def test_tool_call_step_denied_by_data_scope_read_only():
    # roadmap 10a.7: ToolCallStep must forward tenant_policy/data_scope from workflow
    # state into evaluate_access() like any other call site (Executor, ADK node).
    async def write_handler(args):
        return {"written": True}

    registry = ToolRegistry()
    registry.register(
        ToolSpecV2(
            name="strategy.gate_evaluation.create",
            description="Create gate evaluation",
            handler=write_handler,
            risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.SCOPED_WRITE,
        )
    )

    policy_engine = PolicyEngine()
    step = ToolCallStep(
        name="step_write",
        tool_name="strategy.gate_evaluation.create",
        tool_registry=registry,
        policy_engine=policy_engine,
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
    )

    outcome = await step.run({"workspace_id": "ws1", "data_scope": DataScope.READ_ONLY})
    assert outcome.status.value == "FAILED"
    assert "denied by policy" in outcome.error.lower()


@pytest.mark.asyncio
async def test_tool_call_step_in_workflow_requires_approval():
    async def deploy_handler(args):
        return {"deployed": True}

    registry = ToolRegistry()
    registry.register(
        ToolSpecV2(
            name="ops.deploy.prod",
            description="Deploy prod",
            handler=deploy_handler,
            risk_level=ToolRiskLevel.HIGH,
            tool_permission=ToolPermission.ADMIN_WRITE,
            approval_policy="always",
        )
    )

    policy_engine = PolicyEngine()
    approval_svc = ApprovalService()
    engine = WorkflowEngine(
        tool_registry=registry,
        policy_engine=policy_engine,
        approval_service=approval_svc,
    )

    spec = WorkflowSpec(
        id="test.gov",
        steps=[
            WorkflowStepSpec(id="step_deploy", type=StepType.TOOL_CALL, tool="ops.deploy.prod"),
        ],
    )

    workflow = await engine.execute_spec(spec, initial_state={"workspace_id": "ws1", "workflow_id": "wf-123"})

    assert workflow.status == WorkflowStatus.WAITING_APPROVAL
    assert workflow.pending_approval_id is not None

    # Check approval object in approval_service
    approval = approval_svc.get(workflow.pending_approval_id)
    assert approval.action == "ops.deploy.prod"


@pytest.mark.asyncio
async def test_tool_call_step_does_not_silently_allow_after_policy_relaxes_mid_pause():
    """Regression test cho lỗ hổng đã xác nhận: ToolCallStep.run() gọi lại
    evaluate_access() mỗi lần resume; nếu chỉ dùng kết quả 'hiện tại' một
    mình, policy nới lỏng giữa lúc pause và lúc resume khiến nhánh
    REQUIRE_APPROVAL/kiểm tra approval bị bỏ qua hoàn toàn, tool chạy thẳng
    không qua approval — xem
    COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md Case B."""

    async def deploy_handler(args):
        return {"deployed": True}

    registry = ToolRegistry()
    registry.register(
        ToolSpecV2(
            name="ops.deploy.prod",
            description="Deploy prod",
            handler=deploy_handler,
            risk_level=ToolRiskLevel.HIGH,
            tool_permission=ToolPermission.ADMIN_WRITE,
            approval_policy="always",
        )
    )

    policy_engine = PolicyEngine()
    approval_svc = ApprovalService()
    governance_store = InMemoryGovernanceStateStore()
    step = ToolCallStep(
        name="step_deploy",
        tool_name="ops.deploy.prod",
        tool_registry=registry,
        policy_engine=policy_engine,
        approval_service=approval_svc,
        governance_store=governance_store,
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
    )

    # 1) approval_policy="always" -> REQUIRE_APPROVAL, tạo pending approval, pause.
    first = await step.run({"workspace_id": "ws1", "run_id": "run-1"})
    assert first.status.value == "WAITING_APPROVAL"
    approval_id = first.approval_id

    # 2) Chưa approve — mô phỏng admin nới lỏng policy trước khi resume.
    registry.get("ops.deploy.prod").approval_policy = "never"

    # 3) Resume gọi lại run(): evaluate_access() mới trả ALLOW ("never"), nhưng
    #    accumulator vẫn giữ REQUIRE_APPROVAL từ lần đầu -> vẫn phải qua approval,
    #    KHÔNG được invoke thẳng handler.
    second = await step.run({"workspace_id": "ws1", "run_id": "run-1"})
    assert second.status.value == "WAITING_APPROVAL"
    assert second.approval_id == approval_id

    # 4) Approve, resume lần 3 -> tool được invoke đúng 1 lần, đúng lúc.
    approval_svc.decide(approval_id, reviewer="founder-1", approved=True)
    third = await step.run({"workspace_id": "ws1", "run_id": "run-1"})
    assert third.status.value == "COMPLETED"
    assert third.updates == {"step_deploy": {"deployed": True}}


@pytest.mark.asyncio
async def test_tool_call_step_without_a_run_id_skips_accumulation_and_behaves_as_before():
    # run_id=None: không có key để accumulate theo — giữ hành vi cũ (chỉ
    # dùng evaluate_access() hiện tại), không raise, không đổi behavior.
    async def read_handler(args):
        return {"ok": True}

    registry = ToolRegistry()
    registry.register(
        ToolSpecV2(
            name="reports.read",
            description="Read report",
            handler=read_handler,
            risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.READ_ONLY,
        )
    )

    step = ToolCallStep(
        name="step_read",
        tool_name="reports.read",
        tool_registry=registry,
        policy_engine=PolicyEngine(),
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
    )

    outcome = await step.run({"workspace_id": "ws1"})  # không có run_id/workflow_id trong state

    assert outcome.status.value == "COMPLETED"
    assert outcome.updates == {"step_read": {"ok": True}}
