from apps.cosa.agents.capability_risk_map import CAPABILITY_RISK_BY_ID, capability_risk


def test_known_capability_returns_registered_risk() -> None:
    # operations.task.create_draft is declared risk=MEDIUM in operations_write.py
    assert capability_risk("operations.task.create_draft") == "MEDIUM"


def test_read_capabilities_are_low_or_known() -> None:
    for cap in ("operations.task.list", "operations.task.read"):
        assert capability_risk(cap) in {"LOW", "MEDIUM", "HIGH"}


def test_unknown_capability_returns_none() -> None:
    assert capability_risk("does.not.exist") is None
    assert capability_risk(None) is None
    assert capability_risk("") is None


def test_map_is_populated_from_registered_specs() -> None:
    assert len(CAPABILITY_RISK_BY_ID) >= 8
    assert all(v in {"LOW", "MEDIUM", "HIGH"} for v in CAPABILITY_RISK_BY_ID.values())
