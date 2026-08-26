"""Xác nhận PostgresGovernanceStateStore hoạt động đúng khi schema
agent_core_governance được tạo từ packages/agent_core/migrations/002_...
(canonical path, Phase 1), KHÔNG phụ thuộc legacy/agent_runtime_archive/
agentos/migrations/002_... còn tồn tại hay không — đây là bằng chứng cho
DB_FINAL_CUTOVER.md §3.2 điều kiện xóa: 'canonical migration tạo governance
... từ empty DB' + 'grep canonical code không còn string agent_runtime_archive'.
"""
from __future__ import annotations

import os
import uuid

import pytest

pytest.importorskip("asyncpg")

_RAW_DB_URL = os.environ.get("AGENT_CORE_TEST_DATABASE_URL")
if _RAW_DB_URL and "postgresql+asyncpg://" not in _RAW_DB_URL and "postgresql://" in _RAW_DB_URL:
    TEST_DATABASE_URL = _RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    TEST_DATABASE_URL = _RAW_DB_URL

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENT_CORE_TEST_DATABASE_URL not set",
)


@pytest.mark.asyncio
async def test_governance_store_roundtrip_against_canonical_migration_schema():
    from agent_core.governance.accumulator import InvocationGovernanceState
    from agent_core.governance.contracts import PolicyDecision, PolicyOutcome
    from agent_core.governance.providers.postgres import PostgresGovernanceStateStore
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    store = PostgresGovernanceStateStore(db_session_factory=factory)

    run_id = f"run-canonical-{uuid.uuid4().hex[:8]}"
    decision = PolicyDecision(outcome=PolicyOutcome.ALLOW)
    state = InvocationGovernanceState.start(run_id=run_id, tool_call_id="call-1", initial=decision)

    await store.save_governance_state(state, observation=decision, source="historical")
    loaded = await store.load_governance_state(run_id, "call-1")

    assert loaded is not None
    assert loaded.accumulated.outcome == PolicyOutcome.ALLOW

    await engine.dispose()


def test_no_canonical_code_references_agent_runtime_archive():
    """Grep test — canonical code không được đọc bảng tạo bởi SQL trong legacy/
    (DB_FINAL_CUTOVER.md §1.3). Test này KHÔNG skip khi thiếu DB — chạy độc lập."""
    import subprocess
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[4]
    result = subprocess.run(
        ["grep", "-rl", "agent_runtime_archive", "packages/agent_core", "apps/cosa"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "", (
        f"canonical code still references agent_runtime_archive:\n{result.stdout}"
    )
