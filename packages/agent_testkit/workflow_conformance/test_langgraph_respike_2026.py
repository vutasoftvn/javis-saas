"""Re-spike 2026 của LangGraph làm WorkflowRuntime candidate — chạy THẬT với
Postgres checkpointer, không chỉ đọc lại kết quả spike cũ (2026-08-23).

Yêu cầu env var `AGENT_TEST_DATABASE_URL` (dùng chung format DSN
"postgresql://" thuần — khác `AGENT_DATABASE_URL` dùng "postgresql+asyncpg://"
cho SQLAlchemy, vì `AsyncPostgresSaver` của langgraph dùng driver `psycopg`
riêng, tự quản lý connection string dạng chuẩn). Bỏ qua nếu thiếu
langgraph/asyncpg hoặc không set env var — đúng pattern conformance khác
trong `agent_testkit/`.
"""
from __future__ import annotations

import os

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("psycopg")

TEST_DATABASE_URL_ASYNCPG = os.environ.get("AGENT_TEST_DATABASE_URL")
# AsyncPostgresSaver dùng psycopg (driver "postgresql://" thuần), không phải
# SQLAlchemy — chuyển đổi từ dạng "postgresql+asyncpg://" nếu cần.
TEST_DATABASE_URL_PSYCOPG = (
    TEST_DATABASE_URL_ASYNCPG.replace("postgresql+asyncpg://", "postgresql://", 1)
    if TEST_DATABASE_URL_ASYNCPG
    else None
)

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL_PSYCOPG,
    reason="AGENT_TEST_DATABASE_URL not set — skipping LangGraph re-spike (cần Postgres thật)",
)


def _build_spec():
    from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec

    return WorkflowSpec(
        id="respike_fanout_join",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(id="root", type=StepType.DETERMINISTIC),
            WorkflowStepSpec(id="branch_a", type=StepType.DETERMINISTIC, depends_on=["root"]),
            WorkflowStepSpec(id="branch_b", type=StepType.DETERMINISTIC, depends_on=["root"]),
            WorkflowStepSpec(id="join", type=StepType.DETERMINISTIC, depends_on=["branch_a", "branch_b"]),
        ],
    )


@pytest.mark.asyncio
async def test_langgraph_superstep_isolation_and_reducer_merge():
    """HL-13 liên quan (parallel branch isolation) — 2 nhánh song song ghi
    kết quả riêng, reducer hợp nhất đúng, không mất/ghi đè lẫn nhau."""
    from agent_integrations.langgraph.workflow_runtime import compile_deterministic_workflow

    calls: list[str] = []

    def make_fn(name: str):
        def _fn(results: dict) -> dict:
            calls.append(name)
            return {"ran": name}
        return _fn

    registry = {
        "root": make_fn("root"),
        "branch_a": make_fn("branch_a"),
        "branch_b": make_fn("branch_b"),
        "join": make_fn("join"),
    }
    graph = compile_deterministic_workflow(_build_spec(), registry)
    compiled = graph.compile()

    final_state = await compiled.ainvoke({"results": {}, "completed_steps": []})

    assert set(final_state["completed_steps"]) == {"root", "branch_a", "branch_b", "join"}
    assert final_state["results"]["branch_a"] == {"ran": "branch_a"}
    assert final_state["results"]["branch_b"] == {"ran": "branch_b"}
    # root phải chạy trước 2 nhánh; join phải chạy sau cùng.
    assert calls[0] == "root"
    assert calls[-1] == "join"
    assert set(calls[1:3]) == {"branch_a", "branch_b"}


@pytest.mark.asyncio
async def test_langgraph_pending_write_recovery_after_crash():
    """HL-13 — Pending-writes recovery: nhánh A thành công, nhánh B "crash"
    (raise), sau khi restart (checkpointer/graph instance MỚI, cùng
    thread_id) chỉ nhánh B chạy lại, nhánh A KHÔNG chạy lại (side-effect
    counter chứng minh, không suy đoán từ log)."""
    from agent_integrations.langgraph.workflow_runtime import compile_deterministic_workflow

    call_counts: dict[str, int] = {"root": 0, "branch_a": 0, "branch_b": 0, "join": 0}
    should_fail_branch_b = {"value": True}

    def root_fn(results: dict) -> dict:
        call_counts["root"] += 1
        return {"ok": True}

    def branch_a_fn(results: dict) -> dict:
        call_counts["branch_a"] += 1
        return {"ok": True}

    def branch_b_fn(results: dict) -> dict:
        call_counts["branch_b"] += 1
        if should_fail_branch_b["value"]:
            raise RuntimeError("simulated crash in branch_b")
        return {"ok": True}

    def join_fn(results: dict) -> dict:
        call_counts["join"] += 1
        return {"ok": True}

    registry = {
        "root": root_fn,
        "branch_a": branch_a_fn,
        "branch_b": branch_b_fn,
        "join": join_fn,
    }

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    thread_id = "respike_crash_test_thread"
    config = {"configurable": {"thread_id": thread_id}}

    async with AsyncPostgresSaver.from_conn_string(TEST_DATABASE_URL_PSYCOPG) as checkpointer:
        await checkpointer.setup()
        graph = compile_deterministic_workflow(_build_spec(), registry)
        compiled = graph.compile(checkpointer=checkpointer)

        with pytest.raises(RuntimeError, match="simulated crash in branch_b"):
            await compiled.ainvoke({"results": {}, "completed_steps": []}, config=config)

        assert call_counts["root"] == 1
        assert call_counts["branch_a"] == 1
        assert call_counts["branch_b"] == 1
        assert call_counts["join"] == 0

        # "Restart": tắt cờ lỗi, resume qua CÙNG thread_id, checkpointer instance MỚI
        should_fail_branch_b["value"] = False

    async with AsyncPostgresSaver.from_conn_string(TEST_DATABASE_URL_PSYCOPG) as checkpointer2:
        await checkpointer2.setup()
        graph2 = compile_deterministic_workflow(_build_spec(), registry)
        compiled2 = graph2.compile(checkpointer=checkpointer2)

        final_state = await compiled2.ainvoke(None, config=config)

        assert final_state["results"]["join"] == {"ok": True}

    # Khẳng định cốt lõi của HL-13: root/branch_a KHÔNG chạy lại sau resume,
    # chỉ branch_b (đã fail) và join (chưa từng chạy) chạy.
    assert call_counts["root"] == 1, "root phải KHÔNG chạy lại sau resume (pending-write recovery)"
    assert call_counts["branch_a"] == 1, "branch_a phải KHÔNG chạy lại sau resume"
    assert call_counts["branch_b"] == 2, "branch_b chạy lại đúng 1 lần sau khi fail lần đầu"
    assert call_counts["join"] == 1
