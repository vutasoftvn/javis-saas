import pytest

from agentos.core.policy import (
    PermissionLevel,
    PolicyDecision,
    ToolPermission,
    ToolRiskLevel,
    evaluate_access,
)


def test_roadmap_four_reference_cases():
    """Kiểm tra 4 test cases mẫu được chỉ định trong roadmap phase-1-tenant-rbac.md."""
    assert (
        evaluate_access(
            role="founder",
            tool_risk_level=ToolRiskLevel.CRITICAL,
            agent_permission_level=PermissionLevel.L3_EXECUTE,
            tool_permission=ToolPermission.ADMIN_WRITE,
        )
        == PolicyDecision.ALLOW
    )

    assert (
        evaluate_access(
            role="user",
            tool_risk_level=ToolRiskLevel.CRITICAL,
            agent_permission_level=PermissionLevel.L2_DRAFT,
            tool_permission=ToolPermission.ADMIN_WRITE,
        )
        == PolicyDecision.REQUIRE_APPROVAL
    )

    assert (
        evaluate_access(
            role="auditor",
            tool_risk_level=ToolRiskLevel.LOW,
            agent_permission_level=PermissionLevel.L3_EXECUTE,
            tool_permission=ToolPermission.SCOPED_WRITE,
        )
        == PolicyDecision.DENY
    )

    assert (
        evaluate_access(
            role="auditor",
            tool_risk_level=ToolRiskLevel.LOW,
            agent_permission_level=PermissionLevel.L3_EXECUTE,
            tool_permission=ToolPermission.READ_ONLY,
        )
        == PolicyDecision.ALLOW
    )


# --- Full Matrix Tests ---


@pytest.mark.parametrize("level", list(PermissionLevel))
@pytest.mark.parametrize("risk", list(ToolRiskLevel))
def test_auditor_matrix(level: PermissionLevel, risk: ToolRiskLevel):
    """Auditor: READ_ONLY is ALLOW, any write is DENY across all risks & levels."""
    assert evaluate_access(
        role="auditor",
        agent_permission_level=level,
        tool_risk_level=risk,
        tool_permission=ToolPermission.READ_ONLY,
    ) == PolicyDecision.ALLOW

    for write_perm in (ToolPermission.SCOPED_WRITE, ToolPermission.ADMIN_WRITE):
        assert evaluate_access(
            role="auditor",
            agent_permission_level=level,
            tool_risk_level=risk,
            tool_permission=write_perm,
        ) == PolicyDecision.DENY


@pytest.mark.parametrize("level", list(PermissionLevel))
def test_founder_matrix(level: PermissionLevel):
    """Founder:
    - READ_ONLY -> ALLOW
    - write low/medium -> ALLOW
    - write high/critical -> ALLOW if L3_EXECUTE, else REQUIRE_APPROVAL
    """
    for risk in list(ToolRiskLevel):
        assert evaluate_access(
            role="founder",
            agent_permission_level=level,
            tool_risk_level=risk,
            tool_permission=ToolPermission.READ_ONLY,
        ) == PolicyDecision.ALLOW

    for write_perm in (ToolPermission.SCOPED_WRITE, ToolPermission.ADMIN_WRITE):
        # Low and Medium risks are always allowed for founder
        for risk in (ToolRiskLevel.LOW, ToolRiskLevel.MEDIUM):
            assert evaluate_access(
                role="founder",
                agent_permission_level=level,
                tool_risk_level=risk,
                tool_permission=write_perm,
            ) == PolicyDecision.ALLOW

        # High and Critical risks require L3_EXECUTE
        for risk in (ToolRiskLevel.HIGH, ToolRiskLevel.CRITICAL):
            expected = (
                PolicyDecision.ALLOW
                if level == PermissionLevel.L3_EXECUTE
                else PolicyDecision.REQUIRE_APPROVAL
            )
            assert evaluate_access(
                role="founder",
                agent_permission_level=level,
                tool_risk_level=risk,
                tool_permission=write_perm,
            ) == expected


@pytest.mark.parametrize("role", ["co-founder", "user"])
@pytest.mark.parametrize("level", list(PermissionLevel))
def test_cofounder_and_user_matrix(role: str, level: PermissionLevel):
    """Co-founder & User:
    - READ_ONLY -> ALLOW
    - write low/medium -> ALLOW if agent level >= L2 (L2_DRAFT, L3_EXECUTE), else REQUIRE_APPROVAL
    - write high/critical -> REQUIRE_APPROVAL
    """
    for risk in list(ToolRiskLevel):
        assert evaluate_access(
            role=role,
            agent_permission_level=level,
            tool_risk_level=risk,
            tool_permission=ToolPermission.READ_ONLY,
        ) == PolicyDecision.ALLOW

    for write_perm in (ToolPermission.SCOPED_WRITE, ToolPermission.ADMIN_WRITE):
        for risk in (ToolRiskLevel.LOW, ToolRiskLevel.MEDIUM):
            expected = (
                PolicyDecision.ALLOW
                if level in (PermissionLevel.L2_DRAFT, PermissionLevel.L3_EXECUTE)
                else PolicyDecision.REQUIRE_APPROVAL
            )
            assert evaluate_access(
                role=role,
                agent_permission_level=level,
                tool_risk_level=risk,
                tool_permission=write_perm,
            ) == expected

        for risk in (ToolRiskLevel.HIGH, ToolRiskLevel.CRITICAL):
            assert evaluate_access(
                role=role,
                agent_permission_level=level,
                tool_risk_level=risk,
                tool_permission=write_perm,
            ) == PolicyDecision.REQUIRE_APPROVAL


def test_string_inputs_normalization():
    """Xác nhận evaluate_access nhận chuỗi và chuẩn hóa đúng."""
    assert (
        evaluate_access(
            role="  FOUNDER  ",
            agent_permission_level="L3_EXECUTE",
            tool_risk_level="critical",
            tool_permission="admin_write",
        )
        == PolicyDecision.ALLOW
    )


def test_unknown_role_is_denied():
    """Role không hợp lệ bị từ chối (DENY)."""
    assert (
        evaluate_access(
            role="hacker",
            agent_permission_level=PermissionLevel.L3_EXECUTE,
            tool_risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.READ_ONLY,
        )
        == PolicyDecision.DENY
    )
