"""`PostgresRunRepository.list_runs` trên schema thật.

Bug gốc của lỗi HTTP 500 ở dashboard (`/agent/workforce/dashboard-summary`,
`/exceptions`, `/artifacts`, `/runs`): query còn dùng tên cột cũ
(`agent_spec_id`, `definition_hash`, `metadata`…) không còn trong `agent.runs`
nên Postgres ném UndefinedColumnError. Test InMemory không bắt được lỗi này.
"""

from __future__ import annotations

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
    reason="AGENT_TEST_DATABASE_URL not set — skipping real-Postgres list_runs test",
)


@pytest.mark.asyncio
async def test_list_runs_returns_workspace_runs_newest_first_with_project_scope():
    from agent.contracts.run import RunStatus
    from agent.governance.contracts import ExecutionMode
    from agent.runs.models import RunRecord
    from agent.runs.repository import PostgresRunRepository
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(TEST_DATABASE_URL)
    repo = PostgresRunRepository(async_sessionmaker(engine, expire_on_commit=False))
    ws = f"ws_list_{uuid.uuid4().hex[:8]}"
    try:
        ids = []
        for i in range(3):
            run = RunRecord(
                run_id=f"run_list_{uuid.uuid4().hex[:10]}",
                principal="test-suite",
                root_executable_id="cosa.agents.operations",
                status=RunStatus.RUNNING,
                execution_mode=ExecutionMode.AUTONOMOUS,
                workspace_id=ws,
                project_id="proj_1" if i == 2 else None,
            )
            await repo.create_run(run)
            ids.append(run.run_id)
        other = RunRecord(
            run_id=f"run_list_{uuid.uuid4().hex[:10]}",
            principal="test-suite",
            root_executable_id="cosa.agents.operations",
            status=RunStatus.RUNNING,
            execution_mode=ExecutionMode.AUTONOMOUS,
            workspace_id=f"{ws}_other",
        )
        await repo.create_run(other)

        runs = await repo.list_runs(ws, limit=2)

        assert [r.run_id for r in runs] == [ids[2], ids[1]]
        assert runs[0].project_id == "proj_1"
        assert runs[0].root_executable_id == "cosa.agents.operations"
        assert all(r.workspace_id == ws for r in runs)
    finally:
        await engine.dispose()
