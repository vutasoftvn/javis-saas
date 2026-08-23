"""Integration test: InvocationGovernanceState (đã tích luỹ tại request-time)
sống sót qua 1 lần 'restart process' mô phỏng — 2 PostgresGovernanceStateStore
instance riêng biệt (không share object Python nào), chỉ cùng trỏ 1 Postgres.

ApprovalService vẫn in-memory (chưa nằm trong scope các plan này) nên test
này KHÔNG cố chứng minh toàn bộ approval lifecycle durable — chỉ đúng phần
đã thật sự durable: accumulated PolicyDecision qua GovernanceStateStore.

Yêu cầu env var `AGENTOS_TEST_DATABASE_URL` trỏ tới 1 Postgres đã chạy
migration `agentos/migrations/002_governance_temporal_model.sql`. Bỏ qua
(skip) nếu biến này không được set.
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
async def test_accumulated_governance_state_survives_a_simulated_process_restart(session_factory):
    from agent_core.governance.accumulator import InvocationGovernanceState
    from agent_core.governance.contracts import PolicyDecision, PolicyOutcome, RoleApproval
    from agent_core.governance.providers.postgres import PostgresGovernanceStateStore

    run_id = f"run-{uuid.uuid4().hex[:8]}"
    tool_call_id = "ops.deploy.prod"

    # "Process 1": request-time decision — risk cao -> REQUIRE_APPROVAL, persist.
    store_process_1 = PostgresGovernanceStateStore(db_session_factory=session_factory)
    request_time = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder"))
    state = InvocationGovernanceState.start(run_id=run_id, tool_call_id=tool_call_id, initial=request_time)
    await store_process_1.save_governance_state(state, observation=request_time, source="historical")
    del store_process_1  # mô phỏng process 1 kết thúc — không object nào còn sống

    # "Process 2": store instance HOÀN TOÀN mới, chỉ cùng trỏ Postgres đó.
    store_process_2 = PostgresGovernanceStateStore(db_session_factory=session_factory)
    loaded = await store_process_2.load_governance_state(run_id, tool_call_id)
    assert loaded is not None
    assert loaded.accumulated == request_time

    # Policy đã nới lỏng (ALLOW) trước khi resume — constraint cũ không được xoá.
    resume_time = PolicyDecision(outcome=PolicyOutcome.ALLOW)
    combined = loaded.accumulate(resume_time)
    await store_process_2.save_governance_state(combined, observation=resume_time, source="historical")

    final = await store_process_2.load_governance_state(run_id, tool_call_id)
    assert final is not None
    assert final.accumulated.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert final.accumulated.requirement == RoleApproval(role="founder")
