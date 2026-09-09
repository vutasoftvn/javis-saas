"""COSA Automation MVP — cross-plane contract freeze (Task 1).

Locks the shape of the Automation surface, the single dispatch envelope, and the
002/003 persistence migrations before any handler is written. See
docs/superpowers/plans/2026-09-10-cosa-automation-mvp.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SURFACE = ROOT / "shared/contracts/mvp-surface.json"
ENVELOPE = ROOT / "shared/contracts/automation-envelope.v1.json"

AUTOMATION_IDS = {
    "automation.definition.list",
    "automation.definition.get",
    "automation.definition.configure",
    "automation.definition.publish",
    "automation.definition.suspend",
    "automation.invocation.create",
    "automation.invocation.get",
    "automation.invocation.cancel",
    "automation.run.inspector.read",
    "automation.approval.decide",
    "automation.needs_you.list",
}

ENVELOPE_FIELDS = {
    "schema_version",
    "invocation_id",
    "workspace_id",
    "automation_key",
    "revision",
    "revision_hash",
    "trigger_kind",
    "trigger_identity",
    "correlation_id",
    "requested_at",
}

FORBIDDEN_ENVELOPE_KEYS = {
    "input_payload",
    "input",
    "prompt",
    "credential",
    "secret",
    "connector_grant",
    "authorization",
    "business_document",
    "vault_ref",
}


def _surface() -> list[dict]:
    return json.loads(SURFACE.read_text(encoding="utf-8"))["capabilities"]


def _automation_rows() -> list[dict]:
    return [r for r in _surface() if r["id"] in AUTOMATION_IDS]


def test_all_eleven_automation_capabilities_present():
    ids = {r["id"] for r in _surface()}
    assert AUTOMATION_IDS <= ids, f"missing: {AUTOMATION_IDS - ids}"


def test_automation_capabilities_metadata_shape():
    for row in _automation_rows():
        assert row["plane"] == "company", row["id"]
        assert row["source_kind"] == "company_db", row["id"]
        assert row["requires_workspace"] is True, row["id"]
        assert row["owner"] == "company-operations", row["id"]
        assert row["schema"] == f"{row['id']}.v1", row["id"]
        assert row["path"].startswith("/operations/automation/"), row["id"]
        for field in ("backend_test", "flutter_test", "integration_test", "frontend_symbol"):
            val = row.get(field)
            assert isinstance(val, str) and val.strip(), f"{row['id']}.{field}"


def test_automation_routes_are_unique_within_surface():
    seen: set[str] = set()
    for row in _surface():
        key = f"{row['plane']}:{row['method']} {row['path']}"
        assert key not in seen, f"duplicate route {key}"
        seen.add(key)


def test_automation_capabilities_ship_disabled_until_their_task_lands():
    # Rollout is expand-only and one blueprint/surface at a time (spec §9). A
    # capability flips to enabled only in the task that adds its real handler +
    # authorization test + Flutter contract test.
    for row in _automation_rows():
        assert row["enabled"] is False, (
            f"{row['id']} is enabled — its evidence paths must all exist "
            "(see tests/contracts/test_founder_trial_mvp_surface.py)"
        )


def test_dispatch_envelope_is_strict_and_reference_only():
    schema = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    assert schema.get("additionalProperties") is False
    assert set(schema["required"]) == ENVELOPE_FIELDS
    assert set(schema["properties"]) == ENVELOPE_FIELDS
    for forbidden in FORBIDDEN_ENVELOPE_KEYS:
        assert forbidden not in schema["properties"], forbidden
    assert schema["properties"]["schema_version"]["const"] == 1
    assert schema["properties"]["trigger_kind"]["enum"] == ["manual", "schedule", "business_event"]


# --- migrations ------------------------------------------------------------

COMPANY_UP = ROOT / "services/company/operations/migrations/003_cosa_automation_mvp.up.sql"
COMPANY_DOWN = ROOT / "services/company/operations/migrations/003_cosa_automation_mvp.down.sql"
COSA_UP = ROOT / "services/cosa/migrations/003_cosa_automation_mvp.up.sql"
COSA_DOWN = ROOT / "services/cosa/migrations/003_cosa_automation_mvp.down.sql"
AGENT_UP = ROOT / "packages/agent/migrations/003_cosa_automation_mvp.sql"
AGENT_DOWN = ROOT / "packages/agent/migrations/003_cosa_automation_mvp.down.sql"
COSA_RESTORE = ROOT / "services/cosa/migrations/002_restore_control_plane_execution_substrate.up.sql"
AGENT_RESTORE = ROOT / "packages/agent/migrations/002_restore_event_intake_substrate.sql"


def test_all_automation_migration_files_exist():
    for p in (
        COMPANY_UP, COMPANY_DOWN, COSA_UP, COSA_DOWN, AGENT_UP, AGENT_DOWN,
        COSA_RESTORE, AGENT_RESTORE,
    ):
        assert p.exists(), p


def test_company_automation_migration_has_only_local_foreign_keys():
    sql = COMPANY_UP.read_text(encoding="utf-8")
    refs = re.findall(r"REFERENCES\s+([\w.]+)", sql, re.IGNORECASE)
    assert refs, "expected at least one intra-DB FK"
    for target in refs:
        assert target.lower().startswith("operating.automation_"), target


def _strip_sql_comments(sql: str) -> str:
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines())


def test_cosa_automation_dispatch_stores_opaque_references_only():
    body = _strip_sql_comments(COSA_UP.read_text(encoding="utf-8")).lower()
    assert not re.search(r"\breferences\b", body), "control-plane dispatch must hold no FK"
    for leak in ("prompt", "credential", "input_payload", "connector", "business_"):
        assert leak not in body, leak


def test_agent_automation_migration_never_touches_company():
    sql = AGENT_UP.read_text(encoding="utf-8")
    refs = re.findall(r"REFERENCES\s+([\w.]+)", sql, re.IGNORECASE)
    for target in refs:
        assert target.lower().startswith("agent."), target
    lowered = sql.lower()
    for company_token in ("operating.", "strategy.", "commercial.", "finance", "workspace_migrator", "company"):
        assert company_token not in lowered, company_token
