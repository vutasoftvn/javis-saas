# backend/app/tests/agents/test_specialist_registry.py
from workforce.agents.orchestration.specialist_registry import (
    AUTO_START_MAX_RISK,
    DEFAULT_ORCHESTRATION_DOMAINS,
    RISK_ORDER,
    SPECIALIST_REGISTRY,
    SpecialistSpec,
    classify_mission_risk,
)


def test_specialist_registry_has_four_domains():
    assert set(SPECIALIST_REGISTRY.keys()) == {"sales", "finance", "legal", "marketing"}
    assert DEFAULT_ORCHESTRATION_DOMAINS == ("sales", "finance")


def test_classify_mission_risk_picks_highest_tier():
    assert classify_mission_risk(["sales", "finance"]) == "R0"
    assert classify_mission_risk([]) == "R0"


def test_classify_mission_risk_unknown_domain_ignored():
    assert classify_mission_risk(["sales", "does_not_exist"]) == "R0"


def test_risk_order_and_auto_start_threshold_unchanged():
    assert RISK_ORDER == ("R0", "R1", "R2", "R3", "R4")
    assert AUTO_START_MAX_RISK == "R1"
