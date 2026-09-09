"""COSA Automation MVP (Task 5) — manifest resolution, hash verification and
insert-once persistence."""

from __future__ import annotations

import pytest
from agent.runs.repository import InMemoryRunRepository
from agent.workflows.automation_blueprints import (
    AUTOMATION_BLUEPRINT_KEYS,
    build_automation_blueprint_registry,
    get_blueprint_metadata,
    get_blueprint_spec,
)
from agent.workflows.automation_manifest import (
    AutomationManifestError,
    resolve_automation_manifest,
)


def _payload(**over):
    base = {
        "run_id": "run_auto_inv1",
        "invocation_id": "inv1",
        "workspace_id": "ws1",
        "automation_key": "operating.weekly-review",
        "revision": 1,
        "revision_hash": "r" * 64,
        "trigger_kind": "manual",
        "trigger_identity": "req-1",
        "correlation_id": "corr-1",
    }
    base.update(over)
    return base


def _resolve(key="operating.weekly-review", **over):
    return resolve_automation_manifest(
        dispatch_payload=_payload(automation_key=key, **over),
        blueprint_spec=get_blueprint_spec(key),
        blueprint_metadata=get_blueprint_metadata(key),
    )


def test_registry_registers_exactly_four_blueprints():
    reg = build_automation_blueprint_registry()
    assert set(AUTOMATION_BLUEPRINT_KEYS) == {
        "operating.weekly-review",
        "operations.task-follow-up",
        "commercial.outbound-draft",
        "strategy.initiative-health",
    }
    for key in AUTOMATION_BLUEPRINT_KEYS:
        assert reg.current_version(key).definition_hash


def test_resolve_pins_revision_and_blueprint_hash():
    m = _resolve()
    assert m.run_id == "run_auto_inv1"
    assert m.revision_hash == "r" * 64
    assert m.blueprint_hash == get_blueprint_spec("operating.weekly-review").definition_hash
    assert m.pinned_agent_spec_id == "cosa.agents.operations"
    assert "operations.task.read" in m.capability_allowlist


def test_resolve_rejects_unknown_key_and_mismatched_spec():
    with pytest.raises(KeyError):
        get_blueprint_spec("operating.nope")
    with pytest.raises(AutomationManifestError):
        resolve_automation_manifest(
            dispatch_payload=_payload(automation_key="operating.weekly-review"),
            blueprint_spec=get_blueprint_spec("operations.task-follow-up"),
            blueprint_metadata=get_blueprint_metadata("operations.task-follow-up"),
        )


def test_resolve_rejects_missing_fields():
    p = _payload()
    del p["revision_hash"]
    with pytest.raises(AutomationManifestError):
        resolve_automation_manifest(
            dispatch_payload=p,
            blueprint_spec=get_blueprint_spec("operating.weekly-review"),
            blueprint_metadata=get_blueprint_metadata("operating.weekly-review"),
        )


@pytest.mark.asyncio
async def test_persist_is_insert_once_and_hash_verifying():
    repo = InMemoryRunRepository()
    m = _resolve()
    h = m.compute_hash()
    first = await repo.save_automation_manifest(m.run_id, h, m.model_dump(mode="json"))
    assert first["manifest_hash"] == h

    # Same run, same hash -> idempotent no-op.
    again = await repo.save_automation_manifest(m.run_id, h, m.model_dump(mode="json"))
    assert again["manifest_hash"] == h

    # Same run, different hash -> rejected (drift guard).
    with pytest.raises(ValueError):
        await repo.save_automation_manifest(m.run_id, "different" + "0" * 56, {"x": 1})

    loaded = await repo.get_automation_manifest(m.run_id)
    assert loaded is not None and loaded["manifest_hash"] == h


def test_commercial_blueprint_declares_no_delivery_capability():
    meta = get_blueprint_metadata("commercial.outbound-draft")
    assert meta["autonomy_class"] == "draft_only"
    for cap in meta["capability_ids"]:
        assert "send" not in cap and "deliver" not in cap and "email" not in cap
