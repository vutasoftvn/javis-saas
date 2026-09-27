import json

import pytest

from apps.cosa.agents.goal_decomposition import (
    PlanSchemaError,
    build_decomposition_prompt,
    parse_plan_output,
)


def _plan(**over):
    item = {
        "title": "Draft onboarding SOP",
        "decision_reason": "Standardise week-one onboarding",
        "evidence_refs": ["note-1"],
        "suggested_domain": "operations",
        "expected_capability": "operations.sop.draft",
        "depends_on_titles": [],
        "priority": "high",
    }
    item.update(over)
    return json.dumps({"items": [item]})


def test_parses_a_valid_plan():
    items = parse_plan_output(_plan())
    assert len(items) == 1
    assert items[0].title == "Draft onboarding SOP"
    assert items[0].expected_capability == "operations.sop.draft"
    assert items[0].priority == "high"


def test_parses_valid_plan_with_markdown_fence():
    raw = "```json\n" + _plan() + "\n```"
    items = parse_plan_output(raw)
    assert items[0].title == "Draft onboarding SOP"


def test_human_only_item_has_null_domain_and_capability():
    raw = json.dumps(
        {
            "items": [
                {
                    "title": "Interview 3 customers",
                    "decision_reason": "Need qualitative signal for the goal",
                    "evidence_refs": [],
                    "suggested_domain": None,
                    "expected_capability": None,
                }
            ]
        }
    )
    items = parse_plan_output(raw)
    assert items[0].suggested_domain is None
    assert items[0].expected_capability is None
    assert items[0].priority == "medium"


def test_missing_title_raises():
    with pytest.raises(PlanSchemaError):
        parse_plan_output(_plan(title=""))


def test_short_decision_reason_raises():
    with pytest.raises(PlanSchemaError):
        parse_plan_output(_plan(decision_reason="x"))


def test_evidence_refs_not_a_list_raises():
    with pytest.raises(PlanSchemaError):
        parse_plan_output(_plan(evidence_refs="note-1"))


def test_dep_on_unknown_title_raises():
    with pytest.raises(PlanSchemaError):
        parse_plan_output(_plan(depends_on_titles=["Nonexistent"]))


def test_empty_and_non_json_raise():
    with pytest.raises(PlanSchemaError):
        parse_plan_output("")
    with pytest.raises(PlanSchemaError):
        parse_plan_output("not json at all")
    with pytest.raises(PlanSchemaError):
        parse_plan_output(json.dumps({"items": []}))


def test_multi_item_dependency_resolves_between_siblings():
    raw = json.dumps(
        {
            "items": [
                {
                    "title": "A",
                    "decision_reason": "first step",
                    "evidence_refs": [],
                },
                {
                    "title": "B",
                    "decision_reason": "second step",
                    "evidence_refs": [],
                    "depends_on_titles": ["A"],
                },
            ]
        }
    )
    items = parse_plan_output(raw)
    assert items[1].depends_on_titles == ["A"]


def test_prompt_contains_goal_and_schema_guidance():
    prompt = build_decomposition_prompt(
        "Close 3 customer interviews",
        {"lifecycle_stage": "P1_PROBLEM_VALIDATION", "existing_task_titles": ["Old task"]},
    )
    assert "Close 3 customer interviews" in prompt
    assert "expected_capability" in prompt
    assert "P1_PROBLEM_VALIDATION" in prompt
    assert "Old task" in prompt
    assert "JSON" in prompt


def _draft(cap, domain):
    from apps.cosa.agents.goal_decomposition import PlanItemDraft

    return PlanItemDraft(
        title="Do it",
        decision_reason="because it matters",
        evidence_refs=[],
        suggested_domain=domain,
        expected_capability=cap,
    )


_CATALOG = {
    "operations": ["operations.task.list", "strategy.project.get"],
    "strategy": ["strategy.project.get", "strategy.evidence.list"],
    "sales": ["project.crm.read"],
}


def test_validate_plan_capabilities_drops_unknown_capability():
    from apps.cosa.agents.goal_decomposition import validate_plan_capabilities

    [out] = validate_plan_capabilities([_draft("operations.sop.draft", "operations")], _CATALOG)
    assert out.expected_capability is None
    assert out.suggested_domain == "operations"


def test_validate_plan_capabilities_reassigns_domain_to_owner():
    from apps.cosa.agents.goal_decomposition import validate_plan_capabilities

    [out] = validate_plan_capabilities([_draft("project.crm.read", "marketing")], _CATALOG)
    assert out.expected_capability == "project.crm.read"
    assert out.suggested_domain == "sales"


def test_validate_plan_capabilities_keeps_valid_pair_and_does_not_mutate():
    from apps.cosa.agents.goal_decomposition import validate_plan_capabilities

    item = _draft("strategy.project.get", "strategy")
    [out] = validate_plan_capabilities([item], _CATALOG)
    assert (out.suggested_domain, out.expected_capability) == ("strategy", "strategy.project.get")
    assert out is not item


def test_prompt_lists_capability_catalog_and_existing_tasks():
    from apps.cosa.agents.goal_decomposition import build_decomposition_prompt

    prompt = build_decomposition_prompt(
        "Ship v1",
        {
            "lifecycle_stage": "P2_VALIDATION",
            "existing_task_titles": ["Interview 3 customers"],
            "capability_catalog": _CATALOG,
        },
    )
    assert "P2_VALIDATION" in prompt
    assert "- Interview 3 customers" in prompt
    assert "- sales: project.crm.read" in prompt
    assert "operations.sop.draft" not in prompt
