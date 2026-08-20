from app.workforce.agents.governance.policy_engine import PolicyAction


def test_child_cannot_escalate_parent_permission():
    """Delegation must not turn an L0 mission into L3 execution."""
    from app.workforce.agents.delegation.policy import DelegationPolicyEngine

    decision = DelegationPolicyEngine.evaluate(
        parent_permission="read_only",
        child_permission="l3_execute",
        risk_level="R2",
        provider_name="deepseek_harness",
        provider_healthy=True,
    )

    assert decision.action == PolicyAction.DENY


def test_unhealthy_provider_is_denied_without_mock_fallback():
    """Health failure must stop before creating a provider side effect."""
    from app.workforce.agents.delegation.policy import DelegationPolicyEngine

    decision = DelegationPolicyEngine.evaluate(
        parent_permission="l3_execute",
        child_permission="read_only",
        risk_level="R0",
        provider_name="deepseek_harness",
        provider_healthy=False,
    )

    assert decision.action == PolicyAction.DENY


def test_coding_executor_requires_approval_even_for_low_declared_risk():
    """Provider capability risk cannot be hidden by a low-risk step label."""
    from app.workforce.agents.delegation.policy import DelegationPolicyEngine

    decision = DelegationPolicyEngine.evaluate(
        parent_permission="l3_execute",
        child_permission="l3_execute",
        risk_level="R1",
        provider_name="codex_device",
        provider_healthy=True,
    )

    assert decision.action == PolicyAction.REQUIRE_APPROVAL


def test_r2_agent_assignment_is_allowed_with_l3_authority():
    """A healthy in-process medium-risk task may run under existing L3 authority."""
    from app.workforce.agents.delegation.policy import DelegationPolicyEngine

    decision = DelegationPolicyEngine.evaluate(
        parent_permission="l3_execute",
        child_permission="l2_draft",
        risk_level="R2",
        provider_name="in_process",
        provider_healthy=True,
    )

    assert decision.action == PolicyAction.ALLOW
