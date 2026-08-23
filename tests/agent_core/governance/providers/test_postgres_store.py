from __future__ import annotations

import pytest

from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.governance.exceptions import GovernanceStoreConfigurationError
from agent_core.governance.providers.postgres import PostgresGovernanceStateStore


class _FakeResult:
    def __init__(self, rows: list[tuple] | None = None) -> None:
        self._rows = rows or []

    def fetchall(self) -> list[tuple]:
        return self._rows

    def fetchone(self) -> tuple | None:
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(self, fetch_result: _FakeResult | None = None) -> None:
        self.executed: list[tuple[str, dict]] = []
        self.committed = False
        self._fetch_result = fetch_result or _FakeResult()

    async def execute(self, sql, params: dict | None = None):
        self.executed.append((str(sql), params or {}))
        return self._fetch_result

    async def commit(self) -> None:
        self.committed = True

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *exc) -> None:
        return None


def _session_factory(session: _FakeSession):
    return lambda: session


def test_init_without_session_factory_raises_configuration_error():
    with pytest.raises(GovernanceStoreConfigurationError) as exc_info:
        PostgresGovernanceStateStore(db_session_factory=None)
    assert "requires a valid `db_session_factory`" in str(exc_info.value)


@pytest.mark.asyncio
async def test_save_manifest_entry_inserts_into_the_manifest_table():
    session = _FakeSession()
    store = PostgresGovernanceStateStore(db_session_factory=_session_factory(session))
    entry = PinnedSpecIdentity(spec_kind="agent", spec_id="cofounder", spec_version="3", definition_hash="a" * 64)

    await store.save_manifest_entry("run-1", entry)

    assert session.committed is True
    sql, params = session.executed[0]
    assert "INSERT INTO agent_core_governance.spec_resolution_manifest_entries" in sql
    assert params["run_id"] == "run-1"
    assert params["spec_kind"] == "agent"
    assert params["spec_id"] == "cofounder"
    assert params["definition_hash"] == "a" * 64


@pytest.mark.asyncio
async def test_load_manifest_maps_rows_back_into_pinned_spec_identities():
    row = ("agent", "cofounder", "3", "a" * 64)
    session = _FakeSession(fetch_result=_FakeResult(rows=[row]))
    store = PostgresGovernanceStateStore(db_session_factory=_session_factory(session))

    manifest = await store.load_manifest("run-1")

    assert len(manifest.entries) == 1
    assert manifest.entries[0] == PinnedSpecIdentity(
        spec_kind="agent", spec_id="cofounder", spec_version="3", definition_hash="a" * 64
    )
    sql, params = session.executed[0]
    assert "FROM agent_core_governance.spec_resolution_manifest_entries" in sql
    assert params["run_id"] == "run-1"


@pytest.mark.asyncio
async def test_load_manifest_returns_an_empty_manifest_when_nothing_is_stored():
    session = _FakeSession(fetch_result=_FakeResult(rows=[]))
    store = PostgresGovernanceStateStore(db_session_factory=_session_factory(session))

    manifest = await store.load_manifest("unknown-run")

    assert manifest.entries == ()
