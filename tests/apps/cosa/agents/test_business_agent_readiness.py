from __future__ import annotations

import pytest
from agent.contracts.identity import PinnedSkillRef
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import AutonomyLevel

from apps.cosa.agents.capability_readiness import (
    check_agent_spec_readiness,
    check_capability_readiness,
    check_permission_readiness,
    get_skill_required_capabilities,
)
from apps.cosa.agents.specs import COSA_OPERATIONS_AGENT_SPEC


def test_check_capability_readiness_basic():
    assert check_capability_readiness({"strategy.project.get"}, set()) == ["strategy.project.get"]
    assert check_capability_readiness({"a", "b", "c"}, {"b"}) == ["a", "c"]
    assert check_capability_readiness({"a", "b"}, {"a", "b", "c"}) == []


def test_check_permission_readiness_separated_from_capability():
    # Permission readiness chỉ so sánh permissions, không bị lẫn với tools
    missing_perms = check_permission_readiness(
        required={"READ_LOCAL", "WRITE_STAGE"},
        granted={"READ_LOCAL"},
    )
    assert missing_perms == ["WRITE_STAGE"]

    # Không tự grant permission để làm pass readiness
    assert check_permission_readiness({"FINANCE_APPROVE"}, set()) == ["FINANCE_APPROVE"]


def test_operations_lifecycle_skill_missing_tools():
    """Operations pin lifecycle.context-resolver và lifecycle.next-best-action.
    Nếu registry chỉ có operations.task.*, check_capability_readiness phải báo missing
    strategy.project.get và strategy.next_best_action.get.
    """
    lifecycle_required = {"strategy.project.get", "strategy.next_best_action.get"}
    base_available = {
        "operations.task.list",
        "operations.task.read",
        "operations.task.create_draft",
    }
    missing = check_capability_readiness(lifecycle_required, base_available)
    assert missing == ["strategy.next_best_action.get", "strategy.project.get"]


def test_operations_spec_readiness_with_all_capabilities_registered():
    manifests = {
        "lifecycle.context-resolver": {
            "runtime": {"tools": ["strategy.project.get"]},
        },
        "lifecycle.next-best-action": {
            "runtime": {"tools": ["strategy.next_best_action.get"]},
        },
    }

    # Available bao gồm toàn bộ capability_refs của COSA_OPERATIONS_AGENT_SPEC
    all_capabilities = set(COSA_OPERATIONS_AGENT_SPEC.capability_refs)

    missing = check_agent_spec_readiness(
        COSA_OPERATIONS_AGENT_SPEC,
        available_capabilities=all_capabilities,
        skill_manifests=manifests,
    )
    assert missing == []


def test_operations_spec_readiness_reports_missing_capabilities():
    manifests = {
        "lifecycle.context-resolver": {
            "runtime": {"tools": ["strategy.project.get"]},
        },
        "lifecycle.next-best-action": {
            "runtime": {"tools": ["strategy.next_best_action.get"]},
        },
    }

    # Thiếu strategy.project.get
    subset_capabilities = set(COSA_OPERATIONS_AGENT_SPEC.capability_refs) - {"strategy.project.get"}
    missing = check_agent_spec_readiness(
        COSA_OPERATIONS_AGENT_SPEC,
        available_capabilities=subset_capabilities,
        skill_manifests=manifests,
    )
    assert missing == ["strategy.project.get"]
