import pytest
from apps.cosa.governance.initiative_policy import (
    InitiativeRunPolicyDecision,
    assert_initiative_run_allowed,
)
from packages.agent.evaluations.initiative_suite import (
    EvaluationPinSet,
    InitiativeEvaluationResult,
)


def _sample_snapshot(
    lifecycle_state: str = "PILOT",
    autonomy_tier: str = "A1",
    risk_tier: str = "LOW",
    pins: dict | None = None,
):
    return {
        "initiative_id": "init_123",
        "initiative_revision": 1,
        "workspace_id": "ws_test",
        "project_id": "proj_test",
        "lifecycle_state": lifecycle_state,
        "autonomy_tier": autonomy_tier,
        "risk_tier": risk_tier,
        "pins": pins or {"agent_spec_ref": "spec_1", "model_route_ref": "route_1"},
    }


def _sample_run_request(
    workspace_id: str = "ws_test",
    project_id: str = "proj_test",
    autonomy_tier: str = "A1",
    is_protected: bool = False,
    pins: dict | None = None,
):
    class FakeRunRequest:
        def __init__(self):
            self.workspace_id = workspace_id
            self.project_id = project_id
            self.autonomy_tier = autonomy_tier
            self.is_protected = is_protected
            self.pins = pins or {"agent_spec_ref": "spec_1", "model_route_ref": "route_1"}

    return FakeRunRequest()


def test_initiative_policy_lower_autonomy_allowed():
    snapshot = _sample_snapshot(autonomy_tier="A2")
    req = _sample_run_request(autonomy_tier="A1")
    decision = assert_initiative_run_allowed(snapshot, req)
    assert decision.allowed is True
    assert decision.reason_code == "allowed"


def test_initiative_policy_higher_autonomy_denied():
    snapshot = _sample_snapshot(autonomy_tier="A1")
    req = _sample_run_request(autonomy_tier="A2")
    decision = assert_initiative_run_allowed(snapshot, req)
    assert decision.allowed is False
    assert decision.reason_code == "initiative_autonomy_ceiling_exceeded"


def test_initiative_policy_reserved_autonomy_a3_denied():
    snapshot = _sample_snapshot(autonomy_tier="A2")
    req = _sample_run_request(autonomy_tier="A3")
    decision = assert_initiative_run_allowed(snapshot, req)
    assert decision.allowed is False
    assert decision.reason_code == "autonomy_tier_reserved"


def test_initiative_policy_scope_mismatch_denied():
    snapshot = _sample_snapshot()
    req = _sample_run_request(project_id="other_project")
    decision = assert_initiative_run_allowed(snapshot, req)
    assert decision.allowed is False
    assert decision.reason_code == "initiative_scope_mismatch"


def test_initiative_policy_paused_or_retired_denied():
    snapshot_paused = _sample_snapshot(lifecycle_state="PAUSED")
    req = _sample_run_request()
    dec_paused = assert_initiative_run_allowed(snapshot_paused, req)
    assert dec_paused.allowed is False
    assert dec_paused.reason_code == "initiative_lifecycle_paused"

    snapshot_retired = _sample_snapshot(lifecycle_state="RETIRED")
    dec_retired = assert_initiative_run_allowed(snapshot_retired, req)
    assert dec_retired.allowed is False
    assert dec_retired.reason_code == "initiative_lifecycle_retired"


def test_initiative_policy_protected_run_requires_scale_candidate_or_scaled():
    snapshot = _sample_snapshot(lifecycle_state="VALIDATE")
    req = _sample_run_request(is_protected=True)
    decision = assert_initiative_run_allowed(snapshot, req)
    assert decision.allowed is False
    assert decision.reason_code == "initiative_lifecycle_not_scale_candidate_or_scaled"

    snapshot_scaled = _sample_snapshot(lifecycle_state="SCALED")
    decision_scaled = assert_initiative_run_allowed(snapshot_scaled, req)
    assert decision_scaled.allowed is True


def test_initiative_policy_pin_drift_denied():
    snapshot = _sample_snapshot(pins={"agent_spec_ref": "spec_v2"})
    req = _sample_run_request(pins={"agent_spec_ref": "spec_v1"})
    decision = assert_initiative_run_allowed(snapshot, req)
    assert decision.allowed is False
    assert decision.reason_code == "initiative_pin_mismatch"


def test_initiative_policy_evaluation_drift_denied():
    snapshot = _sample_snapshot()
    req = _sample_run_request()
    eval_result = InitiativeEvaluationResult(
        result_id="res_1",
        suite_id="suite_1",
        suite_hash="hash_1",
        workspace_id="ws_test",
        project_id="proj_test",
        initiative_id="init_123",
        pins=EvaluationPinSet(agent_spec_ref="spec_drifted"),
        passed=True,
    )
    decision = assert_initiative_run_allowed(snapshot, req, evaluation_result=eval_result)
    assert decision.allowed is False
    assert decision.reason_code == "evaluation_pin_drift"
