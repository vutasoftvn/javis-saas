"""M6 §3 — sync scope policy."""

from __future__ import annotations

from agent_core.sync import ConflictPolicy, SyncScope, scope_for


def test_control_metadata_syncs_optimistic_on_link():
    p = scope_for("workspace_membership")
    assert p.scope == SyncScope.CONTROL_METADATA
    assert p.syncs is True
    assert p.conflict_policy == ConflictPolicy.OPTIMISTIC


def test_business_module_optimistic_opt_in():
    p = scope_for("task")
    assert p.scope == SyncScope.BUSINESS_MODULE
    assert p.conflict_policy == ConflictPolicy.OPTIMISTIC


def test_finance_legal_requires_human_resolve():
    for et in (
        "financial_transaction",
        "legal_verification_approval",
        "workspace_stage_transition",
        "decision_record",
    ):
        p = scope_for(et)
        assert p.scope == SyncScope.FINANCE_LEGAL, et
        assert p.conflict_policy == ConflictPolicy.HUMAN_RESOLVE, et


def test_credentials_never_sync():
    p = scope_for("connector_authorization")
    assert p.scope == SyncScope.CREDENTIALS
    assert p.syncs is False
    assert p.conflict_policy == ConflictPolicy.NEVER


def test_runs_memory_artifacts_not_synced_by_default():
    for et in ("run", "memory_item", "artifact"):
        assert scope_for(et).syncs is False, et


def test_transient_never_sync():
    assert scope_for("temp_file").scope == SyncScope.TRANSIENT
    assert scope_for("quarantine_object").syncs is False


def test_prefix_fallback():
    assert scope_for("legal_something_new").scope == SyncScope.FINANCE_LEGAL
    assert scope_for("connector_foo").scope == SyncScope.CREDENTIALS


def test_unknown_entity_fails_closed_to_human_resolve():
    p = scope_for("totally_unknown_thing")
    assert p.scope == SyncScope.FINANCE_LEGAL
    assert p.conflict_policy == ConflictPolicy.HUMAN_RESOLVE
