"""Test Startup Core MVP surface manifest and capability contract."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "shared" / "contracts" / "mvp-surface.json"


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_startup_core_capabilities_present():
    contract = load_contract()
    ids = {item["id"] for item in contract["capabilities"]}
    assert {
        "project.loop.read",
        "project.okr.write",
        "project.cycle.write",
        "project.week.write",
        "project.commitment.write",
        "project.task.write",
    } <= ids
    assert not any(
        token in item["id"]
        for item in contract["capabilities"]
        for token in ("bsc", "pestel", "swot", "tows", "maturity", "automation", "founder_trial")
    )


def test_project_capabilities_require_project_and_workspace():
    contract = load_contract()
    for cap in contract["capabilities"]:
        if cap["id"].startswith("project."):
            assert cap.get("requires_workspace") is True, f"{cap['id']} must require workspace"
            assert cap.get("requires_project") is True, f"{cap['id']} must require project"
            assert ":projectId" in cap["path"], f"{cap['id']} path must contain :projectId"


def test_founder_hub_capabilities_all_require_project():
    """Release guard: ALL Founder Hub capabilities must have requires_project: true."""
    contract = load_contract()
    capabilities = contract.get("capabilities", [])

    # Find all Hub/agent capabilities (conversation, message, project_activity)
    hub_caps = [
        cap
        for cap in capabilities
        if "conversation" in cap.get("id", "") or "project_activity" in cap.get("id", "")
    ]

    assert hub_caps, "Should have Founder Hub capabilities (conversation, project_activity) to check"

    for cap in hub_caps:
        cap_id = cap.get("id", "")
        # Every Hub capability must require project
        assert cap.get("requires_project") is True, (
            f"Hub capability {cap_id} missing requires_project: true; "
            f"all Hub operations must be Project-scoped"
        )


def test_no_hub_company_wide_mode():
    """Release guard: Verify no Hub endpoint claims company-wide behavior."""
    contract = load_contract()
    capabilities = contract.get("capabilities", [])

    hub_caps = [
        cap
        for cap in capabilities
        if "conversation" in cap.get("id", "") or "project_activity" in cap.get("id", "")
    ]

    forbidden_patterns = ["company-wide", "all-projects", "all_projects", "default_project"]

    for cap in hub_caps:
        cap_id = cap.get("id", "")
        path = cap.get("path", "")
        schema = cap.get("schema", "")

        for pattern in forbidden_patterns:
            assert pattern not in cap_id.lower(), (
                f"Hub capability {cap_id} contains forbidden pattern '{pattern}'"
            )
            assert pattern not in path.lower(), (
                f"Hub path {path} contains forbidden pattern '{pattern}'"
            )
            assert pattern not in schema.lower(), (
                f"Hub schema {schema} contains forbidden pattern '{pattern}'"
            )


def test_no_hub_github_adapter():
    """Release guard: Verify no GitHub adapter in Hub endpoints."""
    contract = load_contract()
    capabilities = contract.get("capabilities", [])

    hub_caps = [
        cap
        for cap in capabilities
        if "conversation" in cap.get("id", "") or "project_activity" in cap.get("id", "")
    ]

    forbidden_patterns = ["github", "pull_request", "pull-request", "repository", "repo"]

    for cap in hub_caps:
        cap_id = cap.get("id", "")
        path = cap.get("path", "")

        for pattern in forbidden_patterns:
            assert pattern not in cap_id.lower(), (
                f"Hub capability {cap_id} must not reference GitHub ({pattern})"
            )
            assert pattern not in path.lower(), (
                f"Hub path {path} must not reference GitHub ({pattern})"
            )
