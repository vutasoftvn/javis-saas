from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.cosa.observability.metrics import (
    COSA_APPROVALS_TOTAL,
    COSA_APPROVAL_WAIT_SECONDS,
    COSA_MODEL_COST_USD_TOTAL,
    COSA_MODEL_TOKENS_TOTAL,
    COSA_RUNS_TOTAL,
    COSA_RUN_DURATION_SECONDS,
    COSA_SCHEDULER_QUEUE_DEPTH,
    COSA_TOOL_CALLS_TOTAL,
    COSA_WORKER_ACTIVE_LEASES,
    dec_active_leases,
    get_prometheus_metrics_payload,
    inc_active_leases,
    record_approval,
    record_model_tokens,
    record_run_outcome,
    record_tool_call,
    set_active_leases,
    set_scheduler_queue_depth,
)
from apps.cosa.worker.health import WorkerHealthState, create_worker_health_app


def test_record_run_outcome():
    before = COSA_RUNS_TOTAL.labels(outcome="completed")._value.get()
    record_run_outcome("completed", duration_sec=1.5)
    after = COSA_RUNS_TOTAL.labels(outcome="completed")._value.get()
    assert after == before + 1


def test_record_run_outcome_with_duration_histogram():
    """record_run_outcome bơm cả histogram duration khi truyền duration_sec."""
    before_sum = COSA_RUN_DURATION_SECONDS._sum.get()
    record_run_outcome("failed", duration_sec=3.7)
    after_sum = COSA_RUN_DURATION_SECONDS._sum.get()
    assert after_sum > before_sum


def test_record_run_outcome_no_duration():
    """record_run_outcome không bơm histogram khi không có duration_sec."""
    before_sum = COSA_RUN_DURATION_SECONDS._sum.get()
    record_run_outcome("cancelled")  # no duration
    after_sum = COSA_RUN_DURATION_SECONDS._sum.get()
    # histogram sum must NOT change
    assert after_sum == before_sum


def test_record_run_outcome_all_outcomes():
    """Tất cả outcome labels được ghi nhận đúng."""
    for outcome in ("completed", "failed", "waiting_approval", "cancelled"):
        before = COSA_RUNS_TOTAL.labels(outcome=outcome)._value.get()
        record_run_outcome(outcome)
        after = COSA_RUNS_TOTAL.labels(outcome=outcome)._value.get()
        assert after == before + 1, f"Expected counter to increment for outcome={outcome}"


def test_record_tool_call():
    before = COSA_TOOL_CALLS_TOTAL.labels(
        capability="operations.task.list", outcome="success"
    )._value.get()
    record_tool_call("operations.task.list", "success", duration_sec=0.25)
    after = COSA_TOOL_CALLS_TOTAL.labels(
        capability="operations.task.list", outcome="success"
    )._value.get()
    assert after == before + 1


def test_record_approval():
    before = COSA_APPROVALS_TOTAL.labels(decision="approved")._value.get()
    record_approval("approved", wait_duration_sec=30.0)
    after = COSA_APPROVALS_TOTAL.labels(decision="approved")._value.get()
    assert after == before + 1


def test_record_approval_wait_histogram():
    """record_approval bơm cả histogram wait time khi truyền wait_duration_sec."""
    before_sum = COSA_APPROVAL_WAIT_SECONDS._sum.get()
    record_approval("rejected", wait_duration_sec=120.0)
    after_sum = COSA_APPROVAL_WAIT_SECONDS._sum.get()
    assert after_sum > before_sum


def test_record_approval_no_wait():
    """record_approval không lỗi khi không có wait_duration_sec."""
    before = COSA_APPROVALS_TOTAL.labels(decision="expired")._value.get()
    record_approval("expired")  # no wait_duration_sec
    after = COSA_APPROVALS_TOTAL.labels(decision="expired")._value.get()
    assert after == before + 1


def test_record_model_tokens_and_cost_calculation():
    before_input = COSA_MODEL_TOKENS_TOTAL.labels(
        direction="input", model="deepseek-chat"
    )._value.get()
    before_output = COSA_MODEL_TOKENS_TOTAL.labels(
        direction="output", model="deepseek-chat"
    )._value.get()
    before_cost = COSA_MODEL_COST_USD_TOTAL.labels(model="deepseek-chat")._value.get()

    record_model_tokens("deepseek-chat", prompt_tokens=1000, completion_tokens=500)

    after_input = COSA_MODEL_TOKENS_TOTAL.labels(
        direction="input", model="deepseek-chat"
    )._value.get()
    after_output = COSA_MODEL_TOKENS_TOTAL.labels(
        direction="output", model="deepseek-chat"
    )._value.get()
    after_cost = COSA_MODEL_COST_USD_TOTAL.labels(model="deepseek-chat")._value.get()

    assert after_input == before_input + 1000
    assert after_output == before_output + 500
    # DeepSeek default: $0.14/1M prompt + $0.28/1M completion
    # 1000 * 0.14/1M + 500 * 0.28/1M = 0.00014 + 0.00014 = 0.00028
    assert after_cost > before_cost


def test_active_leases_and_queue_depth():
    set_active_leases(5)
    assert COSA_WORKER_ACTIVE_LEASES._value.get() == 5
    inc_active_leases(2)
    assert COSA_WORKER_ACTIVE_LEASES._value.get() == 7
    dec_active_leases(1)
    assert COSA_WORKER_ACTIVE_LEASES._value.get() == 6

    set_scheduler_queue_depth(12)
    assert COSA_SCHEDULER_QUEUE_DEPTH._value.get() == 12


def test_prometheus_metrics_payload():
    payload, content_type = get_prometheus_metrics_payload()
    text = payload.decode("utf-8")
    assert "text/plain" in content_type
    assert "cosa_runs_total" in text
    assert "cosa_run_duration_seconds" in text
    assert "cosa_tool_calls_total" in text
    assert "cosa_model_tokens_total" in text
    assert "cosa_model_cost_usd_total" in text
    assert "cosa_approvals_total" in text
    assert "cosa_approval_wait_seconds" in text
    assert "cosa_worker_active_leases" in text
    assert "cosa_scheduler_queue_depth" in text


def test_worker_health_metrics_endpoint():
    class DummyPlane:
        scheduler = None
        lease_client = None

    health_state = WorkerHealthState(is_running=True)
    app = create_worker_health_app(DummyPlane(), health_state, worker_id="test_worker")
    client = TestClient(app)

    res = client.get("/metrics")
    assert res.status_code == 200
    assert "cosa_runs_total" in res.text
    assert "cosa_worker_active_leases" in res.text
    # All required metric families must be present
    assert "cosa_tool_calls_total" in res.text
    assert "cosa_model_tokens_total" in res.text
    assert "cosa_approvals_total" in res.text
    assert "cosa_scheduler_queue_depth" in res.text
