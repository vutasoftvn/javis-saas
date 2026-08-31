from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from agent.workforce.repository import (
    InMemoryWorkforceRepository,
    PostgresWorkforceRepository,
    WorkforceRepository,
)


def get_workforce_repo(kind: str) -> WorkforceRepository:
    if kind == "in_memory":
        return InMemoryWorkforceRepository()
    elif kind == "postgres":
        db_url = os.environ.get("AGENT_TEST_DATABASE_URL") or os.environ.get("AGENT_DATABASE_URL")
        if not db_url:
            pytest.skip("AGENT_DATABASE_URL not set for PostgresWorkforceRepository test")
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        asyncpg_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine = create_async_engine(asyncpg_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        return PostgresWorkforceRepository(session_factory)
    raise ValueError(f"Unknown kind: {kind}")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["in_memory"])
async def test_assignment_is_scoped_and_pins_a_published_spec(kind: str) -> None:
    workforce_repo = get_workforce_repo(kind)
    assignment = await workforce_repo.create_assignment(
        workspace_id="1001",
        functional_key="campaign_planner",
        spec_id="functional.campaign_planner",
        spec_version="1.0.0",
        definition_hash="sha256:published",
        configured_by="user:1",
    )
    assert assignment.functional_key == "campaign_planner"
    assert assignment.spec_id == "functional.campaign_planner"
    assert assignment.status == "ACTIVE"

    list_a = await workforce_repo.list_assignments("1001")
    assert any(row.assignment_id == assignment.assignment_id for row in list_a)

    list_b = await workforce_repo.list_assignments("2002")
    assert not any(row.assignment_id == assignment.assignment_id for row in list_b)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["in_memory"])
async def test_retire_assignment_updates_status(kind: str) -> None:
    workforce_repo = get_workforce_repo(kind)
    assignment = await workforce_repo.create_assignment(
        workspace_id="1001",
        functional_key="compliance_analyst",
        spec_id="functional.compliance_analyst",
        spec_version="1.0.0",
        definition_hash="sha256:compliance",
        configured_by="user:1",
    )
    retired = await workforce_repo.retire_assignment("1001", assignment.assignment_id)
    assert retired is not None
    assert retired.status == "RETIRED"
    assert retired.retired_at is not None

    active_list = await workforce_repo.list_assignments("1001", status="ACTIVE")
    assert not any(row.assignment_id == assignment.assignment_id for row in active_list)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["in_memory"])
async def test_signal_retry_does_not_create_two_outbox_rows(kind: str) -> None:
    workforce_repo = get_workforce_repo(kind)
    now = datetime.now(UTC)
    run_id = f"run_{uuid4().hex[:8]}"

    sig1 = await workforce_repo.enqueue_runtime_signal(
        workspace_id="1001",
        source_kind="agent_run",
        source_id=run_id,
        sequence=3,
        state="FAILED",
        observed_at=now,
    )
    sig2 = await workforce_repo.enqueue_runtime_signal(
        workspace_id="1001",
        source_kind="agent_run",
        source_id=run_id,
        sequence=3,
        state="FAILED",
        observed_at=now,
    )
    assert sig1.outbox_id == sig2.outbox_id

    pending = await workforce_repo.claim_pending_signals(limit=100)
    matching = [p for p in pending if p.source_id == run_id]
    assert len(matching) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["in_memory"])
async def test_cost_observation_records_and_lists(kind: str) -> None:
    workforce_repo = get_workforce_repo(kind)
    now = datetime.now(UTC)
    run_id = f"run_{uuid4().hex[:8]}"

    obs = await workforce_repo.record_cost_observation(
        workspace_id="1001",
        run_id=run_id,
        provider_key="openai",
        model_key="gpt-4o",
        observed_at=now,
        input_tokens=150,
        output_tokens=300,
        cost_amount=0.005,
        currency="USD",
    )
    assert obs.run_id == run_id
    assert obs.cost_amount == 0.005

    costs = await workforce_repo.list_cost_observations("1001", run_id=run_id)
    assert len(costs) == 1
    assert costs[0].model_key == "gpt-4o"
