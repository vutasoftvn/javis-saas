from __future__ import annotations

import pytest

from agent.governance.accumulator import InvocationGovernanceState
from agent.governance.contracts import (
    ApprovalEvidence,
    PinnedSpecIdentity,
    PolicyDecision,
    PolicyOutcome,
    RoleApproval,
)
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.governance.store import GovernanceStateStore


def test_in_memory_store_satisfies_the_governance_state_store_protocol():
    assert isinstance(InMemoryGovernanceStateStore(), GovernanceStateStore)


@pytest.mark.asyncio
async def test_load_manifest_returns_empty_manifest_when_nothing_saved():
    store = InMemoryGovernanceStateStore()

    manifest = await store.load_manifest("run-1")

    assert manifest.entries == ()


@pytest.mark.asyncio
async def test_save_manifest_entry_then_load_returns_it():
    store = InMemoryGovernanceStateStore()
    entry = PinnedSpecIdentity(spec_kind="agent", spec_id="cofounder", spec_version="3", definition_hash="a" * 64)

    await store.save_manifest_entry("run-1", entry)
    manifest = await store.load_manifest("run-1")

    assert manifest.entries == (entry,)


@pytest.mark.asyncio
async def test_load_governance_state_returns_none_when_nothing_saved():
    store = InMemoryGovernanceStateStore()

    result = await store.load_governance_state("run-1", "call-1")

    assert result is None


@pytest.mark.asyncio
async def test_save_and_load_governance_state_roundtrips():
    store = InMemoryGovernanceStateStore()
    decision = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder"))
    state = InvocationGovernanceState.start(run_id="run-1", tool_call_id="call-1", initial=decision)

    await store.save_governance_state(state, observation=decision, source="historical")
    loaded = await store.load_governance_state("run-1", "call-1")

    assert loaded is not None
    assert loaded.accumulated == decision


@pytest.mark.asyncio
async def test_list_evidence_returns_empty_list_when_nothing_saved():
    store = InMemoryGovernanceStateStore()

    results = await store.list_evidence("call-1")

    assert results == []


@pytest.mark.asyncio
async def test_save_and_list_evidence_roundtrips_scoped_by_invocation():
    store = InMemoryGovernanceStateStore()
    evidence = ApprovalEvidence(approver="founder-1", scope="call-1", decided_at="2026-08-23T10:00:00Z")

    await store.save_evidence(evidence)
    results = await store.list_evidence("call-1")

    assert results == [evidence]
