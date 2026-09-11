"""PostgresProjectActivityRepository — real-Postgres coverage (review
Finding 2, task-3 fix). Mirrors the skip-gated pattern used by
tests/agent/runs/test_cancel_complete_race_postgres.py and
tests/agent/runs/test_postgres_cross_process_resume.py: skipped cleanly when
AGENT_TEST_DATABASE_URL isn't set (this sandbox has no javis_agent_test
database provisioned), but exercises the real 4-step transaction
(append_if_absent) against a live database wherever that env var points at
one — including migration 005's project_activity_idempotency /
project_activity_sequences / project_activity_events tables.

Two properties proven here that InMemoryProjectActivityRepository cannot
prove on its own (single-process, single-connection):
1. append_if_absent is idempotent ACROSS two independent connections — a
   duplicate delivery via a brand-new engine/session still returns the
   original row and consumes no new project_sequence.
2. Concurrent claims for the SAME (workspace_id, project_id) serialize
   through the sequence-cursor row-lock (UPDATE ... SET last_sequence =
   last_sequence + 1 RETURNING) — N concurrent distinct events land on a
   contiguous 1..N sequence with no gaps or duplicates, even though they
   race through separate sessions on the same engine.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest

pytest.importorskip("asyncpg")

_RAW_DB_URL = os.environ.get("AGENT_TEST_DATABASE_URL")
if _RAW_DB_URL and "postgresql+asyncpg://" not in _RAW_DB_URL and "postgresql://" in _RAW_DB_URL:
    TEST_DATABASE_URL = _RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    TEST_DATABASE_URL = _RAW_DB_URL

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENT_TEST_DATABASE_URL not set — skipping real-Postgres project_activity test",
)


def _event(**overrides):
    from agent.project_activity.models import ProjectActivityEventRecord

    base = dict(
        workspace_id="ws_pg_test",
        project_id="proj_pg_test",
        idempotency_key=f"run:{uuid.uuid4().hex[:8]}:run.queued:1",
        kind="run.queued",
        source_type="run",
        source_id=f"run_{uuid.uuid4().hex[:8]}",
        source_version="1",
    )
    base.update(overrides)
    return ProjectActivityEventRecord(**base)


@pytest.mark.asyncio
async def test_append_if_absent_is_idempotent_across_two_connections():
    from agent.project_activity.repository import PostgresProjectActivityRepository
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    workspace_id = f"ws_pg_{uuid.uuid4().hex[:8]}"
    project_id = f"proj_pg_{uuid.uuid4().hex[:8]}"
    idempotency_key = f"run:{uuid.uuid4().hex[:8]}:run.queued:1"

    engine_a = create_async_engine(TEST_DATABASE_URL)
    factory_a = async_sessionmaker(engine_a, expire_on_commit=False)
    repo_a = PostgresProjectActivityRepository(factory_a)

    first = await repo_a.append_if_absent(
        _event(workspace_id=workspace_id, project_id=project_id, idempotency_key=idempotency_key)
    )
    await engine_a.dispose()  # connection A fully closed

    # A brand-new engine/connection (B) attempts the SAME idempotency_key —
    # must return the original row, not create a second one or a second
    # sequence.
    engine_b = create_async_engine(TEST_DATABASE_URL)
    factory_b = async_sessionmaker(engine_b, expire_on_commit=False)
    repo_b = PostgresProjectActivityRepository(factory_b)

    duplicate = await repo_b.append_if_absent(
        _event(workspace_id=workspace_id, project_id=project_id, idempotency_key=idempotency_key)
    )

    assert duplicate.event_id == first.event_id
    assert duplicate.project_sequence == first.project_sequence == 1

    # A genuinely new event (different idempotency_key) on the SAME project
    # via connection B must consume the NEXT sequence, not collide.
    second = await repo_b.append_if_absent(_event(workspace_id=workspace_id, project_id=project_id))
    assert second.project_sequence == 2

    events = await repo_b.list_since(workspace_id=workspace_id, project_id=project_id)
    assert len(events) == 2
    assert [e.project_sequence for e in events] == [1, 2]

    await engine_b.dispose()


@pytest.mark.asyncio
async def test_concurrent_claims_for_same_project_serialize_through_sequence_cursor():
    from agent.project_activity.repository import PostgresProjectActivityRepository
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    workspace_id = f"ws_pg_concurrent_{uuid.uuid4().hex[:8]}"
    project_id = f"proj_pg_concurrent_{uuid.uuid4().hex[:8]}"

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresProjectActivityRepository(factory)

    n = 10
    events = [
        _event(workspace_id=workspace_id, project_id=project_id, source_id=f"run_{i}")
        for i in range(n)
    ]

    # Fire all N claims concurrently — each opens its own session (async
    # engines are pooled, so this genuinely races multiple DB connections
    # against the same (workspace_id, project_id) sequence cursor row.
    results = await asyncio.gather(*(repo.append_if_absent(e) for e in events))

    sequences = sorted(r.project_sequence for r in results)
    assert sequences == list(range(1, n + 1)), (
        f"expected a contiguous 1..{n} sequence with no gaps/duplicates under "
        f"concurrent claims, got {sequences}"
    )

    await engine.dispose()
