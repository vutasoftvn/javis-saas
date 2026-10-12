import asyncio
import os
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio

from agent.workforce.wakeup_ledger import InMemoryWakeupLedger, PostgresWakeupLedger, WakeupEntry

pytestmark = pytest.mark.asyncio

_RAW_DB_URL = os.environ.get("AGENT_TEST_DATABASE_URL")
_PG_URL = _RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://") if _RAW_DB_URL else None

WS1 = "wktest_ws1"
WS2 = "wktest_ws2"


def _e(**over):
    base = dict(
        wake_id="w1",
        workspace_id=WS1,
        assignment_id="a1",
        project_id="p1",
        reason_kind="task_blocked",
        source_ref="task:1",
        hop=0,
        created_at=datetime.now(UTC),
    )
    base.update(over)
    return WakeupEntry(**base)


@pytest_asyncio.fixture(params=["memory", "postgres"])
async def ledger(request):
    if request.param == "memory":
        yield InMemoryWakeupLedger()
        return
    if not _PG_URL:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_PG_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _clean():
        async with factory() as s:
            await s.execute(text("DELETE FROM agent.workforce_wakeups WHERE workspace_id LIKE 'wktest_%'"))
            await s.commit()

    await _clean()
    yield PostgresWakeupLedger(factory)
    await _clean()
    await engine.dispose()


async def test_record_if_absent_dedups_per_source(ledger):
    assert await ledger.record_if_absent(_e()) is True
    assert await ledger.record_if_absent(_e(wake_id="w2")) is False  # cùng (ws, assignment, source_ref)
    assert await ledger.record_if_absent(_e(wake_id="w3", source_ref="task:2")) is True
    assert await ledger.record_if_absent(_e(wake_id="w4", assignment_id="a2")) is True


async def test_count_since_is_workspace_and_assignment_scoped(ledger):
    now = datetime.now(UTC)
    await ledger.record_if_absent(_e(wake_id="w1", source_ref="s1", created_at=now - timedelta(hours=30)))
    await ledger.record_if_absent(_e(wake_id="w2", source_ref="s2", created_at=now - timedelta(hours=1)))
    await ledger.record_if_absent(_e(wake_id="w3", source_ref="s3", workspace_id=WS2))
    assert await ledger.count_since(WS1, "a1", now - timedelta(hours=24)) == 1


async def test_list_unhandled_and_mark_handled(ledger):
    now = datetime.now(UTC)
    await ledger.record_if_absent(_e(wake_id="w1", source_ref="s1", created_at=now - timedelta(minutes=2)))
    await ledger.record_if_absent(_e(wake_id="w2", source_ref="s2", created_at=now - timedelta(minutes=1)))
    await ledger.record_if_absent(_e(wake_id="w3", source_ref="s3", project_id="p2"))
    got = await ledger.list_unhandled(WS1, "a1", "p1")
    assert [x.wake_id for x in got] == ["w1", "w2"]
    assert await ledger.mark_handled(WS1, ["w1"]) == 1
    assert [x.wake_id for x in await ledger.list_unhandled(WS1, "a1", "p1")] == ["w2"]
    assert await ledger.mark_handled(WS2, ["w2"]) == 0  # sai workspace
    assert await ledger.mark_handled(WS1, []) == 0


async def test_concurrent_record_if_absent_single_winner(ledger):
    results = await asyncio.gather(
        ledger.record_if_absent(_e(wake_id="c1", source_ref="same")),
        ledger.record_if_absent(_e(wake_id="c2", source_ref="same")),
    )
    assert sorted(results) == [False, True]


async def test_postgres_ledger_requires_session_factory():
    with pytest.raises(ValueError):
        PostgresWakeupLedger(None)
