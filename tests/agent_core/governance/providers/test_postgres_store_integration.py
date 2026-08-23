"""Integration test cho PostgresGovernanceStateStore chạy với Postgres thật.

Yêu cầu env var `AGENTOS_TEST_DATABASE_URL` trỏ tới 1 Postgres đã chạy migration
`agentos/migrations/002_governance_temporal_model.sql`. Bỏ qua (skip) nếu biến
này không được set — CI không có Postgres vẫn chạy được suite còn lại.
"""
from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio

pytest.importorskip("asyncpg")

TEST_DATABASE_URL = os.environ.get("AGENTOS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENTOS_TEST_DATABASE_URL not set — skipping real-Postgres integration test",
)


@pytest_asyncio.fixture
async def session_factory():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_manifest_entries_roundtrip_and_grow_monotonically(session_factory):
    from agent_core.governance.contracts import PinnedSpecIdentity
    from agent_core.governance.providers.postgres import PostgresGovernanceStateStore

    store = PostgresGovernanceStateStore(db_session_factory=session_factory)
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    first = PinnedSpecIdentity(spec_kind="workflow", spec_id="monthly-review", spec_version="7", definition_hash="a" * 64)
    second = PinnedSpecIdentity(spec_kind="agent", spec_id="legal", spec_version="3", definition_hash="b" * 64)

    await store.save_manifest_entry(run_id, first)
    manifest_after_first = await store.load_manifest(run_id)
    assert manifest_after_first.entries == (first,)

    await store.save_manifest_entry(run_id, second)
    manifest_after_second = await store.load_manifest(run_id)
    assert manifest_after_second.entries == (first, second)  # tăng dần, không mất entry cũ


@pytest.mark.asyncio
async def test_governance_state_roundtrip_and_history_is_append_only(session_factory):
    from agent_core.governance.accumulator import InvocationGovernanceState
    from agent_core.governance.contracts import PolicyDecision, PolicyOutcome, RoleApproval
    from agent_core.governance.providers.postgres import PostgresGovernanceStateStore

    store = PostgresGovernanceStateStore(db_session_factory=session_factory)
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    tool_call_id = "call-1"

    g0 = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="finance_admin"))
    state = InvocationGovernanceState.start(run_id=run_id, tool_call_id=tool_call_id, initial=g0)
    await store.save_governance_state(state, observation=g0, source="historical")

    loaded = await store.load_governance_state(run_id, tool_call_id)
    assert loaded is not None
    assert loaded.accumulated == g0

    g1 = PolicyDecision(outcome=PolicyOutcome.DENY, reasons=("tenant_suspended",))
    state = state.accumulate(g1)
    await store.save_governance_state(state, observation=g1, source="ambient")

    loaded_after_second = await store.load_governance_state(run_id, tool_call_id)
    assert loaded_after_second is not None
    assert loaded_after_second.accumulated.outcome == PolicyOutcome.DENY


@pytest.mark.asyncio
async def test_load_governance_state_returns_none_for_an_unknown_invocation(session_factory):
    from agent_core.governance.providers.postgres import PostgresGovernanceStateStore

    store = PostgresGovernanceStateStore(db_session_factory=session_factory)

    result = await store.load_governance_state(f"run-{uuid.uuid4().hex[:8]}", "unknown-call")

    assert result is None


@pytest.mark.asyncio
async def test_approval_evidence_roundtrip_scoped_by_invocation(session_factory):
    from agent_core.governance.contracts import ApprovalEvidence
    from agent_core.governance.providers.postgres import PostgresGovernanceStateStore

    store = PostgresGovernanceStateStore(db_session_factory=session_factory)
    scope = f"call-{uuid.uuid4().hex[:8]}"
    evidence = ApprovalEvidence(approver="founder-1", scope=scope, decided_at="2026-08-23T10:00:00Z")

    await store.save_evidence(evidence)
    results = await store.list_evidence(scope)

    assert len(results) == 1
    assert results[0].id == evidence.id
    assert results[0].approver == "founder-1"
