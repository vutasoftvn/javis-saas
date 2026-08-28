"""P1 Task 8: EventTriggerEvalSuite ghi lại đủ ngữ cảnh để evidence không
mơ hồ — event schema version, fixtures, policy version, action boundary,
failure injection."""
from agent_core.evals.models import (
    EvalCategory,
    EventFixture,
    EventTriggerEvalSuite,
    InjectionScenario,
)


def _suite(**over):
    base = dict(
        event_schema_version=1,
        input_fixtures=(EventFixture(fixture_id="f1", event_type="operations.task.created.v1"),),
        policy_version="p1",
        expected_action_boundary="artifact_only",
        failure_injection=(
            InjectionScenario(name="duplicate_delivery"),
            InjectionScenario(name="policy_denied"),
        ),
    )
    base.update(over)
    return EventTriggerEvalSuite(**base)


def test_suite_records_schema_version_fixtures_policy_and_injection():
    s = _suite()
    assert s.event_schema_version == 1
    assert s.policy_version == "p1"
    assert {i.name for i in s.failure_injection} == {"duplicate_delivery", "policy_denied"}
    assert s.input_fixtures[0].event_type == "operations.task.created.v1"


def test_suite_maps_to_security_governance_category():
    assert EventTriggerEvalSuite.eval_category() == EvalCategory.SECURITY_GOVERNANCE
