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


import json

from agent_core.governance.accumulator import InvocationGovernanceState
from agent_core.governance.contracts import PolicyDecision, PolicyOutcome, RoleApproval


@pytest.mark.asyncio
async def test_save_governance_state_upserts_state_and_appends_history():
    session = _FakeSession()
    store = PostgresGovernanceStateStore(db_session_factory=_session_factory(session))
    decision = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder"))
    state = InvocationGovernanceState.start(run_id="run-1", tool_call_id="call-1", initial=decision)

    await store.save_governance_state(state, observation=decision, source="historical")

    assert session.committed is True
    assert len(session.executed) == 2
    state_sql, state_params = session.executed[0]
    assert "INSERT INTO agent_core_governance.invocation_governance_state" in state_sql
    assert state_params["run_id"] == "run-1"
    assert state_params["tool_call_id"] == "call-1"
    assert json.loads(state_params["accumulated"])["outcome"] == "REQUIRE_APPROVAL"

    history_sql, history_params = session.executed[1]
    assert "INSERT INTO agent_core_governance.invocation_governance_history" in history_sql
    assert history_params["source"] == "historical"
    assert json.loads(history_params["observation"])["outcome"] == "REQUIRE_APPROVAL"


@pytest.mark.asyncio
async def test_load_governance_state_returns_none_when_nothing_is_stored():
    session = _FakeSession(fetch_result=_FakeResult(rows=[]))
    store = PostgresGovernanceStateStore(db_session_factory=_session_factory(session))

    result = await store.load_governance_state("run-1", "call-1")

    assert result is None


@pytest.mark.asyncio
async def test_load_governance_state_reconstructs_the_accumulated_decision():
    accumulated_json = json.dumps(
        {"outcome": "REQUIRE_APPROVAL", "requirement": {"kind": "role_approval", "role": "founder"}, "reasons": []}
    )
    session = _FakeSession(fetch_result=_FakeResult(rows=[(accumulated_json,)]))
    store = PostgresGovernanceStateStore(db_session_factory=_session_factory(session))

    result = await store.load_governance_state("run-1", "call-1")

    assert result is not None
    assert result.run_id == "run-1"
    assert result.tool_call_id == "call-1"
    assert result.accumulated.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert result.accumulated.requirement == RoleApproval(role="founder")

