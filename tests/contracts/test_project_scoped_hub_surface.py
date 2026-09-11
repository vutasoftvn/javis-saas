"""Project-scoped Founder Hub — cross-plane contract freeze (Task 1).

Locks the shape of the Agent Hub surface (conversations + Project Activity)
before any handler is written. Every capability listed here must require
both workspace and Project — no Company-wide, all-Projects or GitHub-adapter
fallback. See
docs/superpowers/plans/2026-09-11-project-scoped-founder-hub.md.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SURFACE = ROOT / "shared/contracts/mvp-surface.json"

HUB_CAPABILITY_IDS = {
    "agent.conversation.create",
    "agent.conversation.read",
    "agent.conversation.update",
    "agent.conversation.message.create",
    "agent.project_activity.read",
    "agent.project_activity.detail",
    "agent.project_activity.stream",
}

FORBIDDEN_PATH_SUBSTRINGS = (
    "company-wide",
    "all-projects",
    "github",
)


def _surface() -> list[dict]:
    return json.loads(SURFACE.read_text(encoding="utf-8"))["capabilities"]


def _hub_rows() -> list[dict]:
    return [r for r in _surface() if r["id"] in HUB_CAPABILITY_IDS]


def test_all_seven_hub_capabilities_present():
    ids = {r["id"] for r in _surface()}
    assert HUB_CAPABILITY_IDS <= ids, f"missing: {HUB_CAPABILITY_IDS - ids}"


def test_hub_capabilities_require_workspace_and_project():
    for row in _hub_rows():
        assert row["requires_workspace"] is True, row["id"]
        assert row["requires_project"] is True, row["id"]
        assert row["plane"] == "agent", row["id"]
        assert row["source_kind"] == "agent_db", row["id"]
        assert ":projectId" in row["path"], row["id"]
        assert row["schema"] == f"{row['id']}.v1", row["id"]
        for field in ("owner", "frontend_symbol", "backend_test", "flutter_test", "integration_test"):
            val = row.get(field)
            assert isinstance(val, str) and val.strip(), f"{row['id']}.{field}"


def test_hub_capability_paths_have_no_company_wide_or_all_projects_or_github_fallback():
    for row in _hub_rows():
        path_lower = row["path"].lower()
        owner_lower = row["owner"].lower()
        for forbidden in FORBIDDEN_PATH_SUBSTRINGS:
            assert forbidden not in path_lower, f"{row['id']} path contains '{forbidden}'"
            assert forbidden not in owner_lower, f"{row['id']} owner contains '{forbidden}'"


def test_hub_routes_are_unique_within_surface():
    seen: set[str] = set()
    for row in _surface():
        key = f"{row['plane']}:{row['method']} {row['path']}"
        assert key not in seen, f"duplicate route {key}"
        seen.add(key)


def test_generated_python_contract_matches_source_for_hub_capabilities():
    from apps.cosa.api.mvp_contracts_generated import MVP_CAPABILITY_BY_ID

    for cap_id in HUB_CAPABILITY_IDS:
        generated = MVP_CAPABILITY_BY_ID[cap_id]
        assert generated.requires_workspace is True, cap_id
        assert generated.requires_project is True, cap_id
