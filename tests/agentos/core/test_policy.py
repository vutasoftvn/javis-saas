from agentos.core.policy import PermissionClass, PolicyDecision, PolicyEngine


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
