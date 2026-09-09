"""Founder Trial R1 — the Agent Platform is a small generic runtime core.

Locks the retained substrate (conversation, generic run/checkpoint/event/
tool-call, approval/idempotency, exact-hash spec registry, model-provider
policy) and the hard boundary that the agent runtime never carries a Company
database credential or imports Company source.

Physical removal of the out-of-scope route/worker/storage modules
(vault/workforce/schedule/skill-mutation/autopilot/voice/external-automation)
lands with the schema baseline in Task 10; this test guards the boundary and
the retained core in the meantime.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_COMPANY_IMPORT = re.compile(r"^\s*(?:from|import)\s+services(?:\.company)?\b", re.MULTILINE)


def test_agent_runtime_has_no_company_database_dependency():
    source = (ROOT / "apps/cosa/composition/storage_factory.py").read_text()
    assert "WORKSPACE_DATABASE_URL" not in source
    assert not _COMPANY_IMPORT.search(source)


def test_packages_agent_never_imports_company_source():
    offenders: list[str] = []
    for path in (ROOT / "packages/agent").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if _COMPANY_IMPORT.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"packages/agent must not import Company source: {offenders}"


def test_retained_generic_core_modules_exist():
    # Các trụ cột runtime generic được GIỮ LẠI cho R1.
    for rel in (
        "packages/agent/conversations/repository.py",
        "packages/agent/runs/repository.py",
        "packages/agent/runs/stream_events.py",
        "packages/agent/governance/providers/postgres.py",
        "packages/agent/registry/repository.py",
        "packages/agent/registry/resolver.py",
        "packages/agent/scripts/migrate.py",
    ):
        assert (ROOT / rel).exists(), rel


def test_storage_factory_still_wires_retained_bundle():
    source = (ROOT / "apps/cosa/composition/storage_factory.py").read_text()
    for symbol in (
        "ConversationRepository",
        "RunRepository",
        "RunStreamEventRepository",
        "PostgresGovernanceStateStore",
        "SpecRegistryRepository",
    ):
        assert symbol in source, symbol


def test_exact_hash_spec_resolution_is_retained():
    # SpecResolver phải vẫn resolve theo exact definition hash (chống drift khi
    # rolling-deploy nhiều worker) — không được thay bằng "dùng bản mới hơn".
    resolver = (ROOT / "packages/agent/registry/resolver.py")
    assert resolver.exists()
    text = resolver.read_text().lower()
    assert "hash" in text
