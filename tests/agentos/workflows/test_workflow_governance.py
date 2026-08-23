from __future__ import annotations

import pytest

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
