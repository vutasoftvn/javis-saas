"""Test AI Initiative contract routes and capability inventory."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "shared" / "contracts" / "mvp-surface.json"
DART_ENDPOINTS_PATH = ROOT / "frontend" / "lib" / "core" / "network" / "mvp_endpoints.g.dart"
INVENTORY_PATH = ROOT / "docs" / "architecture" / "generated" / "ai-initiative-capability-inventory.json"

EXPECTED_AI_CAPABILITIES = {
    "ai.initiative.read",
    "ai.initiative.write",
    "ai.initiative.transition",
    "ai.initiative.portfolio.read",
}


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_ai_initiative_capabilities_present():
    contract = load_contract()
    ids = {item["id"] for item in contract["capabilities"]}
    missing = EXPECTED_AI_CAPABILITIES - ids
    assert not missing, f"Missing AI initiative capabilities in contract: {missing}"


def test_ai_initiative_capabilities_require_project_and_workspace():
    contract = load_contract()
    ai_caps = [c for c in contract["capabilities"] if c["id"] in EXPECTED_AI_CAPABILITIES]
    assert len(ai_caps) == 4, "Must have exactly 4 AI initiative capabilities"
    for cap in ai_caps:
        assert cap.get("requires_workspace") is True, f"{cap['id']} must require workspace"
        assert cap.get("requires_project") is True, f"{cap['id']} must require project"
        assert ":projectId" in cap["path"], f"{cap['id']} path must contain :projectId"
        assert cap.get("owner") == "company-operations"
        assert cap.get("plane") == "company"


def test_ai_initiative_contract_routes_have_existing_backend_and_flutter_evidence():
    contract = load_contract()
    ai_caps = {c["id"]: c for c in contract["capabilities"] if c["id"] in EXPECTED_AI_CAPABILITIES}
    assert "ai.initiative.transition" in ai_caps, "ai.initiative.transition must be present"
    for cap_id in EXPECTED_AI_CAPABILITIES:
        cap = ai_caps[cap_id]
        assert cap.get("backend_test"), f"{cap_id} must have backend_test"
        assert cap.get("flutter_test"), f"{cap_id} must have flutter_test"
        assert cap.get("integration_test"), f"{cap_id} must have integration_test"


def test_ai_initiative_dart_endpoints_generated():
    content = DART_ENDPOINTS_PATH.read_text(encoding="utf-8")
    expected_members = [
        "aiInitiativeRead",
        "aiInitiativeWrite",
        "aiInitiativeTransition",
        "aiInitiativePortfolioRead",
    ]
    for member in expected_members:
        assert member in content, f"Expected {member} in {DART_ENDPOINTS_PATH}"


def test_ai_initiative_inventory_file_generated():
    assert INVENTORY_PATH.exists(), f"{INVENTORY_PATH} must exist"
    data = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    assert "capabilities" in data
    cap_ids = {c["id"] for c in data["capabilities"]}
    assert EXPECTED_AI_CAPABILITIES <= cap_ids
