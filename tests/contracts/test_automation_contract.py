"""COSA Automation MVP — cross-plane contract freeze (Task 1).

Locks the dispatch envelope and the persistence invariants of the Automation
subsystem. The public Automation capabilities were intentionally removed from
shared/contracts/mvp-surface.json by commit f083ed1b ("feat: define startup core
public contract"; tests/contracts/test_startup_core_mvp_surface.py now asserts that
no "automation" capability id exists). The storage was re-created by the clean-slate
baseline reset (commit d8ed690d) as the restore migrations asserted below, replacing
the deleted 003_cosa_automation_mvp.* files.
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


def test_startup_core_surface_has_no_automation_capabilities():
    # Startup Core publishes no automation capability (f083ed1b). Replaces the former
    # metadata-shape / unique-route / enabled-handler-test loops, which iterated over
    # these (now zero) rows and could not fail. The storage invariants below stay live.
    assert not _automation_rows(), [r["id"] for r in _automation_rows()]


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
# The deleted 003_cosa_automation_mvp.* migrations (commit d8ed690d) were replayed
# verbatim into the restore migrations below. Those files hold other tables too, so
# each invariant is checked only against the statements touching automation objects.

COMPANY_UP = ROOT / "services/company/operations/migrations/002_restore_baseline_gaps.up.sql"
COMPANY_DOWN = ROOT / "services/company/operations/migrations/002_restore_baseline_gaps.down.sql"
# 002 recreated the tables with primary keys only; 041 restores FKs/CHECKs/indexes.
COMPANY_CONSTRAINTS_UP = ROOT / "services/company/operations/migrations/041_restore_automation_constraints.up.sql"
COMPANY_CONSTRAINTS_DOWN = ROOT / "services/company/operations/migrations/041_restore_automation_constraints.down.sql"
COSA_UP = ROOT / "services/cosa/migrations/002_restore_control_plane_dormant_tables.up.sql"
COSA_DOWN = ROOT / "services/cosa/migrations/002_restore_control_plane_dormant_tables.down.sql"
AGENT_UP = ROOT / "packages/agent/migrations/002_restore_knowledge_artifact_automation.sql"
AGENT_DOWN = ROOT / "packages/agent/migrations/002_restore_knowledge_artifact_automation.down.sql"


def _strip_sql_comments(sql: str) -> str:
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines())


def _statements(path: Path, needle: str) -> list[str]:
    """SQL statements (comments stripped) of ``path`` that mention ``needle``."""
    body = _strip_sql_comments(path.read_text(encoding="utf-8"))
    return [st for st in body.split(";") if needle in st.lower()]


def test_all_automation_migration_files_exist():
    for p in (
        COMPANY_UP, COMPANY_DOWN, COMPANY_CONSTRAINTS_UP, COMPANY_CONSTRAINTS_DOWN,
        COSA_UP, COSA_DOWN, AGENT_UP, AGENT_DOWN,
    ):
        assert p.exists(), p


def test_company_automation_migration_has_only_local_foreign_keys():
    stmts = _statements(COMPANY_UP, "operating\".\"automation_")
    created = {
        m.lower()
        for st in stmts
        for m in re.findall(r'create table if not exists "operating"\."(automation_\w+)"', st, re.IGNORECASE)
    }
    assert created >= {
        "automation_definitions",
        "automation_revisions",
        "automation_invocations",
        "automation_invocation_events",
    }, created
    sql = _strip_sql_comments(COMPANY_CONSTRAINTS_UP.read_text(encoding="utf-8"))
    refs = re.findall(r"REFERENCES\s+([\w.]+)", sql, re.IGNORECASE)
    assert len(refs) >= 4, "expected the 4 intra-DB automation FKs"
    for target in refs:
        assert target.lower().startswith("operating.automation_"), target
    assert len(re.findall(r"ON DELETE CASCADE", sql)) == len(refs)


def test_company_automation_constraints_and_unique_indexes_are_restored():
    sql = _strip_sql_comments(COMPANY_CONSTRAINTS_UP.read_text(encoding="utf-8"))
    unique = set(re.findall(r"CREATE UNIQUE INDEX IF NOT EXISTS (\w+)", sql))
    assert unique == {
        "uix_automation_definitions_ws_key",
        "uix_automation_revisions_definition_no",
        "uix_automation_invocations_identity",  # makes select-then-insert idempotency race-safe
        "uix_automation_invocation_events_seq",
    }, unique
    checks = set(re.findall(r"ADD CONSTRAINT (chk_\w+)", sql))
    assert checks == {
        "chk_automation_definitions_lifecycle_state",
        "chk_automation_revisions_autonomy_class",
        "chk_automation_invocations_trigger_kind",
        "chk_automation_invocations_state",
    }, checks
    # Every constraint is guarded and the down migration removes what up adds.
    down = COMPANY_CONSTRAINTS_DOWN.read_text(encoding="utf-8")
    for name in unique | checks | set(re.findall(r"ADD CONSTRAINT (fk_\w+)", sql)):
        assert name in down, f"down migration does not drop {name}"


def test_cosa_automation_dispatch_stores_opaque_references_only():
    stmts = _statements(COSA_UP, "automation_dispatches")
    assert any("create table" in st.lower() for st in stmts), "dispatch table not restored"
    body = "\n".join(stmts).lower()
    assert not re.search(r"\breferences\b", body), "control-plane dispatch must hold no FK"
    for leak in ("prompt", "credential", "input_payload", "connector", "business_"):
        assert leak not in body, leak


def test_agent_automation_migration_never_touches_company():
    stmts = _statements(AGENT_UP, "manifest")
    assert any("automation_run_manifests" in st.lower() for st in stmts), "manifest table not restored"
    sql = "\n".join(stmts)
    for target in re.findall(r"REFERENCES\s+([\w.]+)", sql, re.IGNORECASE):
        assert target.lower().startswith("agent."), target
    lowered = sql.lower()
    for company_token in ("operating.", "strategy.", "commercial.", "finance", "workspace_migrator", "company"):
        assert company_token not in lowered, company_token
