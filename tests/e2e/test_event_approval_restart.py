# R4 (audit 2026-09-06) — CẢNH BÁO: các test trong file này KHÔNG chứng minh
# durability runtime thật. Chúng chỉ truyền 1 dict checkpoint qua
# multiprocessing.Queue rồi chạy lại logic quyết định (takeover/autopilot)
# THUẦN TRONG BỘ NHỚ của process con — không hề chạm CapabilityGateway,
# RunRepository, ApprovalGateDecider hay Postgres thật. 2 PID khác nhau chỉ
# chứng minh multiprocessing.Queue hoạt động, không chứng minh resume sau
# crash đọc lại đúng state từ nguồn sự thật durable (theo CLAUDE.md quy tắc
# 6: "Một test 'resume sau restart' chỉ tạo instance thứ hai trong cùng
# process không được coi là chứng minh").
#
# Bằng chứng durability THẬT (real Postgres, real PostgresRunRepository,
# real subprocess độc lập, verify qua connection MỚI) nằm ở
# tests/agent/runs/test_postgres_cross_process_resume.py — chạy được khi có
# AGENT_TEST_DATABASE_URL trỏ tới Postgres thật (`make agent-test
# AGENT_TEST_DATABASE_URL=...`). File này được GIỮ LẠI (không xoá — cần xác
# nhận người dùng trước khi xoá test theo quy tắc 10 CLAUDE.md) vì vẫn có
# giá trị kiểm tra RIÊNG: đúng logic quyết định founder-takeover/
# autopilot-disabled khi resume nhận 1 checkpoint cho trước — nhưng KHÔNG
# được trích dẫn như bằng chứng cho task R4 (durable runtime).
from __future__ import annotations

import multiprocessing
import os
from typing import Any

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.cross_plane]


def _worker_process_a(checkpoint_queue: multiprocessing.Queue, pid_queue: multiprocessing.Queue) -> None:
    """Process A (SIMULATION, không phải durability thật — xem cảnh báo đầu
    file): giả lập checkpoint WAITING_APPROVAL và đưa qua Queue cho process B,
    KHÔNG persist vào bất kỳ repository/DB thật nào."""
    pid = os.getpid()
    pid_queue.put(pid)

    # Giả lập checkpoint tạo ra bởi Process A
    checkpoint = {
        "run_id": "run_restart_matrix_001",
        "action": "engagement.message.send",
        "checkpoint_id": "chk_001",
        "status": "WAITING_APPROVAL",
        "policy_version": 1,
        "token_bound": "tok_proc_a",
    }
    checkpoint_queue.put(checkpoint)


def _worker_process_b(
    checkpoint_in: dict[str, Any],
    takeover: bool,
    autopilot_enabled: bool,
    result_queue: multiprocessing.Queue,
    pid_queue: multiprocessing.Queue,
) -> None:
    """Process B (SIMULATION, không phải durability thật — xem cảnh báo đầu
    file): nhận checkpoint QUA QUEUE (không đọc từ DB thật), áp logic quyết
    định policy/takeover/autopilot thuần trong bộ nhớ."""
    pid = os.getpid()
    pid_queue.put(pid)

    delivered_count = 0
    completed_runs = []

    # 1. Kiểm tra trạng thái autopilot từ Company: nếu disabled thì không gửi
    if not autopilot_enabled:
        result_queue.put({
            "delivered_message_count": 0,
            "completed_run_ids": [],
            "status": "aborted_autopilot_disabled",
            "checkpoint_after": checkpoint_in,
        })
        return

    # 2. Kiểm tra founder takeover: nếu founder takeover active -> delivered_message_count = 0
    if takeover:
        result_queue.put({
            "delivered_message_count": 0,
            "completed_run_ids": [checkpoint_in["run_id"]],
            "status": "suppressed_founder_takeover",
            "checkpoint_after": checkpoint_in,
        })
        return

    # 3. Normal resume: gửi message thành công và hoàn tất run
    delivered_count += 1
    completed_runs.append(checkpoint_in["run_id"])

    result_queue.put({
        "delivered_message_count": delivered_count,
        "completed_run_ids": completed_runs,
        "status": "completed",
        "checkpoint_after": checkpoint_in,
    })


@pytest.mark.asyncio
async def test_event_approval_restart_simulation_two_pids_ipc_only():
    """SIMULATION — không phải bằng chứng R4 (xem cảnh báo đầu file).
    Chỉ chứng minh multiprocessing.Queue chuyển 1 dict giữa 2 PID khác nhau
    và logic quyết định ở process nhận đúng — KHÔNG chạm Postgres/repository
    thật. Bằng chứng durability thật: xem
    tests/agent/runs/test_postgres_cross_process_resume.py.
    """
    ctx = multiprocessing.get_context("spawn")
    chk_queue = ctx.Queue()
    pid_queue = ctx.Queue()

    # Step 1: Chạy Process A
    proc_a = ctx.Process(target=_worker_process_a, args=(chk_queue, pid_queue))
    proc_a.start()
    proc_a.join(timeout=10)
    assert proc_a.exitcode == 0

    first_worker_pid = pid_queue.get(timeout=5)
    approval_checkpoint_before_restart = chk_queue.get(timeout=5)
    original_run_id = approval_checkpoint_before_restart["run_id"]

    # Step 2: Chạy Process B (resume cùng checkpoint)
    res_queue = ctx.Queue()
    proc_b = ctx.Process(
        target=_worker_process_b,
        args=(approval_checkpoint_before_restart, False, True, res_queue, pid_queue),
    )
    proc_b.start()
    proc_b.join(timeout=10)
    assert proc_b.exitcode == 0

    resumed_worker_pid = pid_queue.get(timeout=5)
    b_result = res_queue.get(timeout=5)

    delivered_message_count = b_result["delivered_message_count"]
    completed_run_ids = b_result["completed_run_ids"]
    approval_checkpoint_after_restart = b_result["checkpoint_after"]

    # Invariant kiểm chứng:
    assert first_worker_pid != resumed_worker_pid
    assert delivered_message_count == 1
    assert completed_run_ids == [original_run_id]
    assert approval_checkpoint_after_restart == approval_checkpoint_before_restart


@pytest.mark.asyncio
async def test_event_approval_restart_founder_takeover_decision_logic():
    """SIMULATION (xem cảnh báo đầu file) — kiểm logic thuần: founder takeover
    trước resume phải delivered_message_count=0. Không chứng minh durability."""
    ctx = multiprocessing.get_context("spawn")
    res_queue = ctx.Queue()
    pid_queue = ctx.Queue()

    checkpoint = {
        "run_id": "run_restart_takeover_002",
        "action": "engagement.message.send",
        "checkpoint_id": "chk_002",
        "status": "WAITING_APPROVAL",
    }

    proc = ctx.Process(
        target=_worker_process_b,
        args=(checkpoint, True, True, res_queue, pid_queue),
    )
    proc.start()
    proc.join(timeout=10)
    assert proc.exitcode == 0

    res = res_queue.get(timeout=5)
    assert res["delivered_message_count"] == 0
    assert res["status"] == "suppressed_founder_takeover"


@pytest.mark.asyncio
async def test_event_approval_restart_autopilot_disabled_decision_logic():
    """SIMULATION (xem cảnh báo đầu file) — kiểm logic thuần: không re-enable
    autopilot nếu trạng thái đã disabled trong Company. Không chứng minh
    durability."""
    ctx = multiprocessing.get_context("spawn")
    res_queue = ctx.Queue()
    pid_queue = ctx.Queue()

    checkpoint = {
        "run_id": "run_restart_disabled_003",
        "action": "engagement.message.send",
        "checkpoint_id": "chk_003",
        "status": "WAITING_APPROVAL",
    }

    proc = ctx.Process(
        target=_worker_process_b,
        args=(checkpoint, False, False, res_queue, pid_queue),
    )
    proc.start()
    proc.join(timeout=10)
    assert proc.exitcode == 0

    res = res_queue.get(timeout=5)
    assert res["delivered_message_count"] == 0
    assert res["status"] == "aborted_autopilot_disabled"
