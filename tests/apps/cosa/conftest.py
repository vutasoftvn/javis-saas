from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent_core.runs.models import RunRecord
from agent_core.runs.repository import PostgresRunRepository
from agent_core.runs.stream_events import PostgresRunStreamEventRepository, RunStreamEventRecord


@pytest.fixture
def postgres_dsn() -> str:
    """Fixture providing PostgreSQL DSN for integration tests.

    Reads DATABASE_URL from environment, substituting 'postgres' hostname
    with '127.0.0.1' (since container DNS doesn't work from host).

    Also converts to async driver (postgresql+asyncpg) for SQLAlchemy async."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")

    # Substitute docker-compose hostname 'postgres' with host IP
    if "postgresql://" in url:
        url = url.replace("@postgres:", "@127.0.0.1:")
    elif "postgres://" in url:
        url = url.replace("postgres://", "postgresql://").replace("@postgres:", "@127.0.0.1:")

    # Convert to async driver for SQLAlchemy
    if "postgresql://" in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")

    return url


@pytest.fixture
def db_session_factory(postgres_dsn):
    """Fixture providing async SQLAlchemy session factory."""
    engine = create_async_engine(postgres_dsn)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def run_id_with_events(db_session_factory):
    """Fixture creating test run and events in the database.

    Inserts:
    1. A RunRecord in agent_core.runs (needed for tenant check in SSE endpoint)
    2. 3-4 RunStreamEventRecords in agent_conversation.run_stream_events (for replay)

    The run and events are created with tenant scopes matching what the
    override_authenticated_identity test helper expects:
    - company_id: "test_company_1"
    - workspace_id: "test_ws_1"
    """

    async def _insert_data():
        run_id = f"run_test_{uuid.uuid4().hex[:12]}"
        conversation_id = "conv_test_1"

        # Create run record first (needed for tenant check)
        run_repo = PostgresRunRepository(db_session_factory)
        run = RunRecord(
            run_id=run_id,
            company_id="test_company_1",  # Must match override_authenticated_identity
            workspace_id="test_ws_1",
            conversation_id=conversation_id,
            principal="user:test_user",
            root_executable_id="cosa.operations",
            root_executable_kind="agent",
        )
        await run_repo.create_run(run)

        # Create stream events
        stream_repo = PostgresRunStreamEventRepository(db_session_factory)
        events = [
            RunStreamEventRecord(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.started",
                payload={"context": "test"},
                correlation_id="corr_1",
                created_at=datetime.now(timezone.utc),
            ),
            RunStreamEventRecord(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.step_completed",
                payload={"step": 1, "result": "ok"},
                correlation_id="corr_2",
                created_at=datetime.now(timezone.utc),
            ),
            RunStreamEventRecord(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.step_completed",
                payload={"step": 2, "result": "ok"},
                correlation_id="corr_3",
                created_at=datetime.now(timezone.utc),
            ),
            RunStreamEventRecord(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.completed",
                payload={"status": "success"},
                correlation_id="corr_4",
                created_at=datetime.now(timezone.utc),
            ),
        ]

        for event in events:
            await stream_repo.append(event)

        return run_id

    return asyncio.run(_insert_data())
