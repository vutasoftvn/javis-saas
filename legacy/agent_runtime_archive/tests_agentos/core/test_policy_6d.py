from __future__ import annotations

import pytest

from agentos.core.policy import (
    DataScope,
    ExecutionMode,
    PermissionLevel,
    PolicyDecision,
    PolicyEngine,
    TenantPolicyDecision,
    ToolPermission,
    ToolRiskLevel,
    evaluate_access,
)


def test_data_scope_read_only_overrides_write_to_deny():
    # Founder + L3_EXECUTE with low risk write tool is normally ALLOW,
    # but DataScope.READ_ONLY forces DENY.
    decision = evaluate_access(
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
        tool_risk_level=ToolRiskLevel.LOW,
        tool_permission=ToolPermission.SCOPED_WRITE,
        data_scope=DataScope.READ_ONLY,
    )
    assert decision == PolicyDecision.DENY


def test_data_scope_read_only_permits_read_only_tool():
    decision = evaluate_access(
        role="user",
        agent_permission_level=PermissionLevel.L1_SUGGEST,
        tool_risk_level=ToolRiskLevel.LOW,
        tool_permission=ToolPermission.READ_ONLY,
        data_scope=DataScope.READ_ONLY,
    )
    assert decision == PolicyDecision.ALLOW


def test_autonomous_safe_mode_denies_high_and_critical_risk():
    # Autonomous safe mode cannot wait for human approval -> high risk is strictly DENIED
    decision_high = evaluate_access(
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
        tool_risk_level=ToolRiskLevel.HIGH,
        tool_permission=ToolPermission.SCOPED_WRITE,
        execution_mode=ExecutionMode.AUTONOMOUS_SAFE,
    )
    assert decision_high == PolicyDecision.DENY

    decision_critical = evaluate_access(
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
        tool_risk_level=ToolRiskLevel.CRITICAL,
        tool_permission=ToolPermission.ADMIN_WRITE,
        execution_mode=ExecutionMode.AUTONOMOUS_SAFE,
    )
    assert decision_critical == PolicyDecision.DENY


def test_autonomous_safe_mode_allows_low_risk():
    decision = evaluate_access(
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
        tool_risk_level=ToolRiskLevel.LOW,
        tool_permission=ToolPermission.SCOPED_WRITE,
        execution_mode=ExecutionMode.AUTONOMOUS_SAFE,
    )
    assert decision == PolicyDecision.ALLOW


def test_interactive_mode_requires_approval_for_high_risk():
    # Interactive mode prioritizes interactive human approval for high risk write
    decision_user = evaluate_access(
        role="user",
        agent_permission_level=PermissionLevel.L2_DRAFT,
        tool_risk_level=ToolRiskLevel.HIGH,
        tool_permission=ToolPermission.SCOPED_WRITE,
        execution_mode=ExecutionMode.INTERACTIVE,
    )
    assert decision_user == PolicyDecision.REQUIRE_APPROVAL

    # Founder at L3 retains full autonomy in interactive mode
    decision_founder = evaluate_access(
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
        tool_risk_level=ToolRiskLevel.HIGH,
        tool_permission=ToolPermission.SCOPED_WRITE,
        execution_mode=ExecutionMode.INTERACTIVE,
    )
    assert decision_founder == PolicyDecision.ALLOW


def test_tenant_policy_intersection():
    # Company policy blocks tool -> DENY
    decision_deny = evaluate_access(
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
        tool_risk_level=ToolRiskLevel.LOW,
        tool_permission=ToolPermission.SCOPED_WRITE,
        tenant_policy=TenantPolicyDecision.DENY,
    )
    assert decision_deny == PolicyDecision.DENY

    # Company policy requires approval for all operations -> REQUIRE_APPROVAL
    decision_req = evaluate_access(
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
        tool_risk_level=ToolRiskLevel.LOW,
        tool_permission=ToolPermission.READ_ONLY,
        tenant_policy=TenantPolicyDecision.REQUIRE_APPROVAL,
    )
    assert decision_req == PolicyDecision.REQUIRE_APPROVAL


def test_policy_engine_evaluates_full_6_dimensions():
    engine = PolicyEngine()
    decision = engine.evaluate_access(
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
        tool_risk_level=ToolRiskLevel.LOW,
        tool_permission=ToolPermission.SCOPED_WRITE,
        tenant_policy=TenantPolicyDecision.ALLOW,
        execution_mode=ExecutionMode.APPROVED_WORKFLOW,
        data_scope=DataScope.WORKSPACE,
        run_id="run_6d",
    )
    assert decision == PolicyDecision.ALLOW
