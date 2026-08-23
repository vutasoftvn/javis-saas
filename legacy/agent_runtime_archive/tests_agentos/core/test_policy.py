from agentos.core.policy import (
    PERMISSION_CLASS_RISK_MAPPING,
    PROTECTED_CORE_RESOURCES,
    ExecutionMode,
    PermissionClass,
    PermissionLevel,
    PolicyDecision,
    PolicyEngine,
    evaluate_execution_mode,
)


class _RecordingAuditSink:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def record(self, **kwargs) -> None:
        self.calls.append(kwargs)


def test_evaluate_records_every_decision_to_the_audit_sink():
    sink = _RecordingAuditSink()
    engine = PolicyEngine(audit_sink=sink)

    engine.evaluate(PermissionClass.ACCESS_SECRET, run_id="run-1")

    assert sink.calls == [
        {
            "event_type": "policy.evaluated",
            "run_id": "run-1",
            "subject": "ACCESS_SECRET",
            "decision": "DENY",
        }
    ]


def test_read_local_is_allowed_by_default():
    engine = PolicyEngine()
    assert engine.evaluate(PermissionClass.READ_LOCAL) == PolicyDecision.ALLOW


def test_access_secret_is_denied_by_default():
    engine = PolicyEngine()
    assert engine.evaluate(PermissionClass.ACCESS_SECRET) == PolicyDecision.DENY


def test_financial_action_requires_approval_by_default():
    engine = PolicyEngine()
    assert engine.evaluate(PermissionClass.FINANCIAL_ACTION) == PolicyDecision.REQUIRE_APPROVAL


def test_custom_table_overrides_default():
    engine = PolicyEngine({PermissionClass.SEND_MESSAGE: PolicyDecision.ALLOW})
    assert engine.evaluate(PermissionClass.SEND_MESSAGE) == PolicyDecision.ALLOW


# --- evaluate_for_agent (ADR-014: PermissionLevel L0-L3A-L3, port từ legacy) ---


def test_evaluate_for_agent_critical_risk_always_requires_approval_regardless_of_level():
    engine = PolicyEngine()
    for level in PermissionLevel:
        assert (
            engine.evaluate_for_agent(
                agent_permission_level=level, tool_risk_level="critical", tool_permission="admin_write"
            )
            == PolicyDecision.REQUIRE_APPROVAL
        )


def test_evaluate_for_agent_l0_read_denies_any_write():
    engine = PolicyEngine()
    assert (
        engine.evaluate_for_agent(
            agent_permission_level=PermissionLevel.L0_READ, tool_risk_level="low", tool_permission="read_only"
        )
        == PolicyDecision.ALLOW
    )
    assert (
        engine.evaluate_for_agent(
            agent_permission_level=PermissionLevel.L0_READ, tool_risk_level="low", tool_permission="scoped_write"
        )
        == PolicyDecision.DENY
    )


def test_evaluate_for_agent_l1_suggest_requires_approval_for_any_write():
    engine = PolicyEngine()
    assert (
        engine.evaluate_for_agent(
            agent_permission_level=PermissionLevel.L1_SUGGEST, tool_risk_level="low", tool_permission="scoped_write"
        )
        == PolicyDecision.REQUIRE_APPROVAL
    )


def test_evaluate_for_agent_l2_draft_allows_low_risk_scoped_write_only():
    engine = PolicyEngine()
    assert (
        engine.evaluate_for_agent(
            agent_permission_level=PermissionLevel.L2_DRAFT, tool_risk_level="low", tool_permission="scoped_write"
        )
        == PolicyDecision.ALLOW
    )
    assert (
        engine.evaluate_for_agent(
            agent_permission_level=PermissionLevel.L2_DRAFT,
            tool_risk_level="medium",
            tool_permission="scoped_write",
        )
        == PolicyDecision.REQUIRE_APPROVAL
    )


def test_evaluate_for_agent_l3a_requires_approval_for_execution():
    engine = PolicyEngine()
    assert (
        engine.evaluate_for_agent(
            agent_permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
            tool_risk_level="low",
            tool_permission="admin_write",
        )
        == PolicyDecision.REQUIRE_APPROVAL
    )


def test_evaluate_for_agent_l3_execute_allows_low_and_medium_risk():
    engine = PolicyEngine()
    assert (
        engine.evaluate_for_agent(
            agent_permission_level=PermissionLevel.L3_EXECUTE, tool_risk_level="medium", tool_permission="admin_write"
        )
        == PolicyDecision.ALLOW
    )
    assert (
        engine.evaluate_for_agent(
            agent_permission_level=PermissionLevel.L3_EXECUTE, tool_risk_level="high", tool_permission="admin_write"
        )
        == PolicyDecision.REQUIRE_APPROVAL
    )


def test_evaluate_for_agent_records_to_audit_sink():
    sink = _RecordingAuditSink()
    engine = PolicyEngine(audit_sink=sink)

    engine.evaluate_for_agent(
        agent_permission_level=PermissionLevel.L0_READ,
        tool_risk_level="low",
        tool_permission="read_only",
        run_id="run-1",
    )

    assert sink.calls == [
        {
            "event_type": "policy.evaluated_for_agent",
            "run_id": "run-1",
            "subject": "L0_READ:low:read_only",
            "decision": "ALLOW",
        }
    ]


def test_permission_class_risk_mapping_covers_every_permission_class():
    assert set(PERMISSION_CLASS_RISK_MAPPING) == set(PermissionClass)


# --- evaluate_execution_mode (ADR-014, port từ legacy) ---


def test_evaluate_execution_mode_autonomous_safe_denies_destructive_capability():
    assert evaluate_execution_mode(ExecutionMode.AUTONOMOUS_SAFE, "delete_record") == PolicyDecision.DENY


def test_evaluate_execution_mode_autonomous_safe_allows_low_risk_capability():
    assert evaluate_execution_mode(ExecutionMode.AUTONOMOUS_SAFE, "read_record") == PolicyDecision.ALLOW


def test_evaluate_execution_mode_approved_workflow_requires_approval_for_critical():
    decision = evaluate_execution_mode(ExecutionMode.APPROVED_WORKFLOW, "anything", risk_level="critical")
    assert decision == PolicyDecision.REQUIRE_APPROVAL


def test_evaluate_execution_mode_interactive_requires_approval_for_send():
    decision = evaluate_execution_mode(ExecutionMode.INTERACTIVE, "send_email")
    assert decision == PolicyDecision.REQUIRE_APPROVAL


def test_evaluate_execution_mode_protects_core_resources_from_write_capabilities():
    decision = evaluate_execution_mode(
        ExecutionMode.INTERACTIVE, "write_file", target_resource="config/policies/main.yaml"
    )
    assert decision == PolicyDecision.REQUIRE_APPROVAL


def test_evaluate_execution_mode_does_not_protect_unrelated_resources():
    decision = evaluate_execution_mode(ExecutionMode.INTERACTIVE, "write_file", target_resource="notes/scratch.md")
    assert decision == PolicyDecision.ALLOW


def test_protected_core_resources_matches_ported_legacy_list():
    assert PROTECTED_CORE_RESOURCES == frozenset(
        {"identity.md", "soul.md", "agents.md", "policies", "platform_prompt_templates", "system_assets"}
    )
