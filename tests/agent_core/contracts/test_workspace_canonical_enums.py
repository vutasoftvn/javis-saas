"""M0 contract freeze — round-trip cho enum canonical sinh từ shared/contracts/enums.json.

Xem docs/architecture/plans/2026-08-29-cosa-workspace-canonical/M0-contract-freeze.md
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_core.contracts.enums_generated import (
    LEGACY_PROJECT_STAGE_TO_CANONICAL,
    LEGACY_WORKSPACE_STAGE_TO_CANONICAL,
    LegalEntityStatus,
    ProjectLifecycleStage,
    ProjectStatus,
    RuntimeMode,
    SyncPolicy,
    SyncStatus,
    WorkspaceLifecycleStage,
    WorkspaceStatus,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENUM_SRC = _REPO_ROOT / "shared/contracts/enums.json"

_ENUM_CLASSES = {
    "workspace_lifecycle_stage": WorkspaceLifecycleStage,
    "project_lifecycle_stage": ProjectLifecycleStage,
    "workspace_status": WorkspaceStatus,
    "project_status": ProjectStatus,
    "runtime_mode": RuntimeMode,
    "sync_policy": SyncPolicy,
    "sync_status": SyncStatus,
    "legal_entity_status": LegalEntityStatus,
}


@pytest.fixture(scope="module")
def source_spec() -> dict:
    return json.loads(_ENUM_SRC.read_text())


def test_generated_python_matches_source(source_spec: dict) -> None:
    """Mọi enum + đúng thứ tự value khớp JSON nguồn."""
    for name, cls in _ENUM_CLASSES.items():
        expected = source_spec["enums"][name]["values"]
        assert [m.value for m in cls] == expected, name


@pytest.mark.parametrize("name", list(_ENUM_CLASSES))
def test_round_trip_every_value(name: str, source_spec: dict) -> None:
    cls = _ENUM_CLASSES[name]
    for wire in source_spec["enums"][name]["values"]:
        assert cls.from_wire(wire).to_wire() == wire
        assert str(cls.from_wire(wire)) == wire


@pytest.mark.parametrize("name", list(_ENUM_CLASSES))
def test_unknown_value_raises_not_silent_default(name: str) -> None:
    cls = _ENUM_CLASSES[name]
    with pytest.raises(ValueError, match="Unknown"):
        cls.from_wire("__NOT_A_REAL_VALUE__")


def test_no_legacy_s_codes_leak_into_canonical() -> None:
    for cls in (WorkspaceLifecycleStage, ProjectLifecycleStage):
        assert not any(m.value.startswith("S") for m in cls)
    assert all(m.value.startswith("W") for m in WorkspaceLifecycleStage)
    assert all(m.value.startswith("P") for m in ProjectLifecycleStage)


def test_legacy_migration_maps_cover_all_targets(source_spec: dict) -> None:
    ws_targets = {v for v in LEGACY_WORKSPACE_STAGE_TO_CANONICAL.values()}
    assert ws_targets == {m.value for m in WorkspaceLifecycleStage}
    proj_targets = {v for v in LEGACY_PROJECT_STAGE_TO_CANONICAL.values()}
    assert proj_targets == {m.value for m in ProjectLifecycleStage}
    # nguồn JSON và mã sinh khớp nhau
    assert LEGACY_WORKSPACE_STAGE_TO_CANONICAL == source_spec["migration_maps"][
        "legacy_workspace_stage_to_canonical"
    ]
    assert LEGACY_PROJECT_STAGE_TO_CANONICAL == source_spec["migration_maps"][
        "legacy_project_stage_to_canonical"
    ]
