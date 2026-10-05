"""Tests for AI Initiative evaluation suite, immutable hashing and material pin drift (Task 7)."""

from __future__ import annotations

from agent.evaluations.initiative_suite import (
    AiEvaluationCase,
    AiEvaluationSuite,
    EvaluationPinSet,
    InitiativeEvaluationResult,
    assert_evaluation_current,
)


def test_agent_spec_hash_change_invalidates_a_passing_initiative_evaluation():
    pins = EvaluationPinSet(
        agent_spec_ref="cosa.agents.operations",
        agent_spec_hash="hash-initial-12345",
        prompt_hash="prompt-hash-1",
    )
    passing_result = InitiativeEvaluationResult(
        result_id="res-1",
        suite_id="suite-1",
        suite_hash="hash-suite",
        workspace_id="ws-1",
        project_id="proj-1",
        initiative_id="init-1",
        pins=pins,
        passed=True,
    )
    changed_snapshot = {
        "pins": {
            "agent_spec_ref": "cosa.agents.operations",
            "agent_spec_hash": "hash-changed-99999",
            "prompt_hash": "prompt-hash-1",
        }
    }
    assert (
        assert_evaluation_current(changed_snapshot, passing_result).code
        == "evaluation_pin_drift"
    )


def test_immutable_suite_creation_and_deterministic_hash():
    pins = EvaluationPinSet(
        agent_spec_ref="cosa.agents.operations",
        agent_spec_hash="abc",
        workflow_ref="workflow.alpha",
    )
    cases = [
        AiEvaluationCase(
            case_id="case-1",
            category="structural",
            description="Verify no raw shell execution",
            fixture_ref="fixtures/cases/structural_1.json",
        )
    ]
    suite1 = AiEvaluationSuite.create(
        suite_id="s1",
        workspace_id="ws1",
        project_id="p1",
        initiative_id="init1",
        revision=1,
        pins=pins,
        cases=cases,
    )
    suite2 = AiEvaluationSuite.create(
        suite_id="s1",
        workspace_id="ws1",
        project_id="p1",
        initiative_id="init1",
        revision=1,
        pins=pins,
        cases=cases,
    )
    assert suite1.suite_hash == suite2.suite_hash
    assert len(suite1.suite_hash) == 64


def test_matching_pins_assert_current():
    pins = EvaluationPinSet(
        agent_spec_ref="cosa.agents.operations",
        agent_spec_hash="abc",
        prompt_hash="p123",
    )
    result = InitiativeEvaluationResult(
        result_id="res-1",
        suite_id="s1",
        suite_hash="shash",
        workspace_id="ws1",
        project_id="p1",
        initiative_id="init1",
        pins=pins,
        passed=True,
    )
    snap = {
        "pins": {
            "agent_spec_ref": "cosa.agents.operations",
            "agent_spec_hash": "abc",
            "prompt_hash": "p123",
        }
    }
    check = assert_evaluation_current(snap, result)
    assert check.is_current is True
    assert check.code is None
