"""P1 Task 8: một EventTriggerRule ghi/proposal chỉ được enable khi có
immutable eval/promotion evidence khớp fingerprint hiện tại. Drift ⇒ reject."""
import pytest

from agent.evals.promotion import PromotionEvidence
from agent.governance.contracts import PinnedSpecIdentity as GovPinned
from apps.cosa.events.trigger_policy import EventTriggerRule, PinnedSpecIdentity
from apps.cosa.events.trigger_promotion import can_enable_trigger

FP_NOW = {"cosa.agent": "hash_A", "skill.x": "hash_B"}


def _rule(mode="artifact_only", evidence_ref="ev_1", event_schema_version=1):
    return EventTriggerRule(
        rule_id="r1", workspace_id="ws_1", event_type="operations.task.created.v1",
        agent_spec=PinnedSpecIdentity(id="cosa.agent", version="1.0.0", definition_hash="hash_A"),
        mode=mode, max_runs_per_aggregate_per_day=1, required_capabilities=(),
        enabled=False, eval_evidence_ref=evidence_ref, event_schema_version=event_schema_version,
    )


def _evidence(*, passed=True, fps=None, action_boundary="artifact_only", event_schema_version=1):
    return PromotionEvidence(
        target_ref=GovPinned(spec_kind="agent", spec_id="cosa.agent",
                             spec_version="1.0.0", definition_hash="hash_A"),
        required_eval_run_ids=["run_1"],
        observed_fingerprints=dict(fps or FP_NOW),
        policy_version="p1",
        policy_checks_passed=passed,
        check_details={"action_boundary": action_boundary,
                       "event_schema_version": event_schema_version},
    )


def test_denied_without_evidence():
    g = can_enable_trigger(_rule(evidence_ref=None), None, FP_NOW, policy_version="p1")
    assert not g.allowed and g.reason == "no_eval_evidence"


def test_denied_when_checks_failed():
    g = can_enable_trigger(_rule(), _evidence(passed=False), FP_NOW, policy_version="p1")
    assert not g.allowed


def test_denied_on_stale_fingerprint():
    g = can_enable_trigger(_rule(), _evidence(fps={"cosa.agent": "hash_OLD"}),
                           {"cosa.agent": "hash_NEW"}, policy_version="p1")
    assert not g.allowed and g.reason == "stale_evidence"


def test_denied_on_changed_event_schema_version():
    g = can_enable_trigger(_rule(event_schema_version=2),
                           _evidence(event_schema_version=1), FP_NOW, policy_version="p1")
    assert not g.allowed and g.reason == "event_schema_changed"


def test_denied_on_policy_version_mismatch():
    g = can_enable_trigger(_rule(), _evidence(), FP_NOW, policy_version="p2")
    assert not g.allowed


def test_artifact_only_evidence_enables_artifact_only_not_write():
    ev = _evidence(action_boundary="artifact_only")
    assert can_enable_trigger(_rule("artifact_only"), ev, FP_NOW, policy_version="p1").allowed
    g = can_enable_trigger(_rule("write"), ev, FP_NOW, policy_version="p1")
    assert not g.allowed and g.reason == "action_boundary_exceeded"


def test_write_rule_requires_human_approval_even_with_matching_evidence():
    ev = _evidence(action_boundary="write")
    g = can_enable_trigger(_rule("write"), ev, FP_NOW, policy_version="p1")
    assert g.allowed and g.requires_human_approval is True


def test_proposal_rule_within_write_boundary_allowed_no_human_approval():
    ev = _evidence(action_boundary="write")
    g = can_enable_trigger(_rule("proposal"), ev, FP_NOW, policy_version="p1")
    assert g.allowed and g.requires_human_approval is False


def test_customer_support_autopilot_write_rule_promotion_gate():
    ev = _evidence(action_boundary="write")
    autopilot_rule = EventTriggerRule(
        rule_id="r_ap_1",
        workspace_id="ws_1",
        event_type="engagement.message.received.v1",
        agent_spec=PinnedSpecIdentity(
            id="cosa.agents.customer_support_autopilot",
            version="1.1.0",
            definition_hash="hash_A",
        ),
        mode="write",
        max_runs_per_aggregate_per_day=10,
        required_capabilities=("engagement.message.send", "engagement.assignment.write"),
        enabled=False,
        eval_evidence_ref="ev_1",
    )
    g = can_enable_trigger(autopilot_rule, ev, FP_NOW, policy_version="p1")
    assert g.allowed is True
    assert g.requires_human_approval is True
