from __future__ import annotations

import os
from datetime import datetime, timezone
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent_core.evals.artifacts import EvalCaseResult, EvalRun, EvalSuite
from agent_core.evals.repositories import InMemoryEvalRepository, PostgresEvalRepository
from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.registry.repository import SpecVersionHashConflictError


def _target_ref() -> PinnedSpecIdentity:
    return PinnedSpecIdentity(spec_kind="agent", spec_id="cofounder", spec_version="17", definition_hash="a" * 64)


@pytest.mark.asyncio
async def test_publish_suite_is_immutable_and_idempotent():
    repo = InMemoryEvalRepository()
    suite = EvalSuite(id="cofounder-core", version="1", target_kind="agent", target_id="cofounder", case_ids=["c1"])

    published1 = await repo.publish_suite(suite)
    assert published1.definition_hash == suite.with_hash().definition_hash

    published2 = await repo.publish_suite(suite)
    assert published2.definition_hash == published1.definition_hash

    changed = EvalSuite(id="cofounder-core", version="1", target_kind="agent", target_id="cofounder", case_ids=["c2"])
    with pytest.raises(SpecVersionHashConflictError):
        await repo.publish_suite(changed)


@pytest.mark.asyncio
async def test_get_suite_returns_none_when_not_published():
    repo = InMemoryEvalRepository()

    result = await repo.get_suite("does.not.exist", "1")

    assert result is None


@pytest.mark.asyncio
async def test_create_run_and_get_run_roundtrip():
    repo = InMemoryEvalRepository()
    run = EvalRun(target_ref=_target_ref())

    created = await repo.create_run(run)
    fetched = await repo.get_run(created.run_id)

    assert fetched is not None
    assert fetched.run_id == created.run_id
    assert fetched.status == "running"


@pytest.mark.asyncio
async def test_update_run_status_changes_status_and_pass_rate():
    repo = InMemoryEvalRepository()
    run = await repo.create_run(EvalRun(target_ref=_target_ref()))

    updated = await repo.update_run_status(run.run_id, "completed", pass_rate=0.9)

    assert updated.status == "completed"
    assert updated.pass_rate == 0.9
    refetched = await repo.get_run(run.run_id)
    assert refetched.status == "completed"


@pytest.mark.asyncio
async def test_record_case_result_and_list_by_run():
    repo = InMemoryEvalRepository()
    run = await repo.create_run(EvalRun(target_ref=_target_ref()))

    await repo.record_case_result(EvalCaseResult(eval_run_id=run.run_id, case_id="c1", passed=True, score=1.0))
    await repo.record_case_result(EvalCaseResult(eval_run_id=run.run_id, case_id="c2", passed=False, score=0.0))

    results = await repo.list_case_results(run.run_id)

    assert len(results) == 2
    assert {r.case_id for r in results} == {"c1", "c2"}


def _pg_session_factory():
    url = os.environ.get(
        "AGENT_CORE_DATABASE_URL",
        "postgresql+asyncpg://javis_app:CHANGE_ME@localhost:5432/javis",
    )
    engine = create_async_engine(url)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_postgres_eval_repository_publish_and_get_suite_roundtrip():
    repo = PostgresEvalRepository(_pg_session_factory())
    suite = EvalSuite(
        id="test.eval_suite.pg_1", version="1", target_kind="agent", target_id="cofounder", case_ids=["c1"]
    )

    published = await repo.publish_suite(suite)
    fetched = await repo.get_suite("test.eval_suite.pg_1", "1")

    assert fetched is not None
    assert fetched.definition_hash == published.definition_hash


@pytest.mark.asyncio
async def test_postgres_eval_repository_run_and_case_result_roundtrip():
    repo = PostgresEvalRepository(_pg_session_factory())
    session_factory = _pg_session_factory()

    # Seed 1 case thật để thoả FK agent_evals.results.case_id (ngoài phạm vi
    # EvalRepository publish — chỉ cần tồn tại cho test integration này).
    async with session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO agent_evals.suites (suite_id, name, target_kind, target_id, version)
                VALUES ('test.eval_suite.pg_2', 'test', 'agent', 'cofounder', '1')
                ON CONFLICT (suite_id) DO NOTHING
                """
            )
        )
        await session.execute(
            text(
                """
                INSERT INTO agent_evals.cases (case_id, suite_id)
                VALUES ('test.case.pg_1', 'test.eval_suite.pg_2')
                ON CONFLICT (case_id) DO NOTHING
                """
            )
        )
        await session.commit()

    target_ref = PinnedSpecIdentity(
        spec_kind="agent", spec_id="cofounder", spec_version="17", definition_hash="a" * 64
    )
    run = await repo.create_run(EvalRun(target_ref=target_ref))

    updated = await repo.update_run_status(run.run_id, "completed", pass_rate=1.0)
    assert updated.status == "completed"

    result = await repo.record_case_result(
        EvalCaseResult(eval_run_id=run.run_id, case_id="test.case.pg_1", passed=True, score=1.0)
    )
    results = await repo.list_case_results(run.run_id)

    assert result.eval_run_id == run.run_id
    assert len(results) == 1
    assert results[0].case_id == "test.case.pg_1"
