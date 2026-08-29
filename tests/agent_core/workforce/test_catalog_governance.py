"""M7 §1/§5 — functional AgentSpec catalog + title-grants-no-capability governance."""

from __future__ import annotations

import pytest
from agent_core.workforce import (
    FUNCTIONAL_AGENT_CATALOG,
    CapabilityBoundaryError,
    WorkforceAssignment,
    assert_within_capability_boundary,
    build_functional_spec,
    capability_change_requires_new_spec,
    catalog_keys,
    execution_capabilities,
)


def test_catalog_entries_are_within_their_own_boundary():
    for key, entry in FUNCTIONAL_AGENT_CATALOG.items():
        assert_within_capability_boundary(key, entry.capability_refs)  # no raise


def test_build_functional_spec_pins_capabilities_and_hash():
    spec = build_functional_spec("cashflow_planner")
    assert spec.id == "functional.cashflow_planner"
    assert spec.definition_hash
    assert spec.capability_refs == [
        "finance.transaction.read",
        "finance.cashflow.forecast",
        "finance.payment.propose",
    ]
    assert spec.metadata["title"] == "Cashflow Planner"
    # hash bất biến theo nội dung
    assert build_functional_spec("cashflow_planner").definition_hash == spec.definition_hash


def test_unknown_key_raises():
    with pytest.raises(KeyError):
        build_functional_spec("nope")
    with pytest.raises(CapabilityBoundaryError):
        assert_within_capability_boundary("nope", [])


def test_capability_outside_boundary_rejected():
    with pytest.raises(CapabilityBoundaryError, match="ngoài ranh giới"):
        assert_within_capability_boundary(
            "cashflow_planner",
            ["finance.transaction.read", "finance.payment.execute"],  # execute không cho
        )


def test_campaign_planner_cannot_gain_spend_capability():
    with pytest.raises(CapabilityBoundaryError):
        assert_within_capability_boundary(
            "campaign_planner", ["marketing.campaign.plan", "marketing.campaign.publish"]
        )


def test_title_does_not_grant_capability():
    spec = build_functional_spec("cashflow_planner")
    # gán persona "CFO" — title cấp cao nhưng KHÔNG thêm capability
    assignment = WorkforceAssignment(
        workspace_id="1001",
        member_id="m-1",
        functional_key="cashflow_planner",
        agent_spec_id=spec.id,
        agent_spec_version=spec.version,
        definition_hash=spec.definition_hash or "",
        role_title="CFO",
        persona="Chief Financial Officer",
        department="Finance",
    )
    caps = execution_capabilities(assignment, spec)
    assert caps == list(spec.capability_refs)
    assert "finance.payment.execute" not in caps
    assert "finance.payment.approve" not in caps


def test_execution_capabilities_rejects_mismatched_spec():
    a_spec = build_functional_spec("cashflow_planner")
    other = build_functional_spec("compliance_analyst")
    assignment = WorkforceAssignment(
        workspace_id="1001",
        member_id="m-1",
        functional_key="cashflow_planner",
        agent_spec_id=a_spec.id,
        agent_spec_version=a_spec.version,
        definition_hash=a_spec.definition_hash or "",
    )
    with pytest.raises(CapabilityBoundaryError):
        execution_capabilities(assignment, other)


def test_capability_change_requires_new_spec():
    spec = build_functional_spec("cashflow_planner")
    assert capability_change_requires_new_spec(spec, spec.capability_refs) is False
    assert (
        capability_change_requires_new_spec(
            spec, [*spec.capability_refs, "finance.payment.execute"]
        )
        is True
    )


def test_catalog_keys_sorted_and_nonempty():
    keys = catalog_keys()
    assert keys == sorted(keys)
    assert "founder_office_orchestrator" in keys
