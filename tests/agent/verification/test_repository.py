import asyncio
import os
from datetime import UTC, datetime

import pytest
import pytest_asyncio

from agent.verification.repository import (
    InMemoryVerificationReportRepository,
    PostgresVerificationReportRepository,
    VerificationReport,
)

pytestmark = pytest.mark.asyncio


def _report(**over):
    base = dict(
        report_id="vr_1",
        workspace_id="ws1",
        project_id="p1",
        task_id="t1",
        run_id="wga_task_1_ab12cd34",
        verifier_run_id=None,
        verdict="PASS",
        mode="deterministic",
        criteria_results=[{"id": "c1", "verdict": "pass"}],
        criteria_hash="h1",
        output_hash="o1",
        created_at=datetime.now(UTC),
    )
    base.update(over)
    return VerificationReport(**base)


_RAW_DB_URL = os.environ.get("AGENT_TEST_DATABASE_URL")
_PG_URL = _RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://") if _RAW_DB_URL else None
requires_pg = pytest.mark.skipif(not _PG_URL, reason="AGENT_TEST_DATABASE_URL not set")


@pytest_asyncio.fixture(params=["memory", "postgres"])
async def repo(request):
    if request.param == "memory":
        yield InMemoryVerificationReportRepository()
        return
    if not _PG_URL:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_PG_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _clean():
        async with factory() as s:
            await s.execute(
                text("DELETE FROM agent.verification_reports WHERE workspace_id LIKE 'vrtest_%'")
            )
            await s.commit()

    await _clean()
    yield PostgresVerificationReportRepository(factory)
    await _clean()
    await engine.dispose()


def _ws(name: str) -> str:
    return f"vrtest_{name}"


async def test_create_if_absent_is_idempotent_per_run(repo):
    ws = _ws("a")
    first = await repo.create_if_absent(_report(workspace_id=ws))
    second = await repo.create_if_absent(_report(workspace_id=ws, report_id="vr_2", verdict="FAIL"))
    assert second.report_id == first.report_id == "vr_1"
    assert second.verdict == "PASS"
    assert first.criteria_results == [{"id": "c1", "verdict": "pass"}]


async def test_get_for_run_is_workspace_scoped(repo):
    await repo.create_if_absent(_report(workspace_id=_ws("a")))
    assert await repo.get_for_run(_ws("a"), "wga_task_1_ab12cd34") is not None
    assert await repo.get_for_run(_ws("b"), "wga_task_1_ab12cd34") is None


async def test_list_for_task_newest_first_and_scoped(repo):
    ws = _ws("a")
    await repo.create_if_absent(
        _report(
            report_id="vr_a",
            run_id="r1",
            workspace_id=ws,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    await repo.create_if_absent(
        _report(
            report_id="vr_b",
            run_id="r2",
            workspace_id=ws,
            created_at=datetime(2026, 1, 2, tzinfo=UTC),
        )
    )
    await repo.create_if_absent(_report(report_id="vr_c", run_id="r3", workspace_id=_ws("b")))
    out = await repo.list_for_task(ws, "t1")
    assert [r.report_id for r in out] == ["vr_b", "vr_a"]


async def test_concurrent_create_if_absent_creates_one_row(repo):
    ws = _ws("conc")
    results = await asyncio.gather(
        *[
            repo.create_if_absent(_report(workspace_id=ws, report_id=f"vr_c{i}", run_id="same"))
            for i in range(8)
        ]
    )
    assert len({r.report_id for r in results}) == 1
    assert len(await repo.list_for_task(ws, "t1")) == 1


def test_postgres_repository_requires_session_factory():
    with pytest.raises(ValueError):
        PostgresVerificationReportRepository(None)


async def test_list_for_task_clamps_limit_to_at_least_one(repo):
    ws = _ws("clamp")
    for i in range(3):
        await repo.create_if_absent(
            _report(
                report_id=f"vr_{i}",
                run_id=f"r{i}",
                workspace_id=ws,
                created_at=datetime(2026, 1, 1 + i, tzinfo=UTC),
            )
        )
    assert [r.report_id for r in await repo.list_for_task(ws, "t1", limit=0)] == ["vr_2"]
    assert len(await repo.list_for_task(ws, "t1", limit=-5)) == 1
    assert len(await repo.list_for_task(ws, "t1", limit=10_000)) == 3


async def test_list_for_task_breaks_created_at_ties_by_report_id_desc(repo):
    ws = _ws("tie")
    same = datetime(2026, 1, 1, tzinfo=UTC)
    for rid in ("vr_a", "vr_c", "vr_b"):
        await repo.create_if_absent(
            _report(report_id=rid, run_id=f"run_{rid}", workspace_id=ws, created_at=same)
        )
    out = await repo.list_for_task(ws, "t1")
    assert [r.report_id for r in out] == ["vr_c", "vr_b", "vr_a"]


async def test_naive_created_at_is_rejected():
    with pytest.raises(ValueError):
        _report(created_at=datetime(2026, 1, 1))
