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
