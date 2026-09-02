"""Test helper tiến trình — không cần service thật, chỉ spawn `python -c`."""

from __future__ import annotations

import sys

from tests.e2e.stack._process import pick_free_port, spawn, terminate_all, wait_until_ready


def test_pick_free_port_returns_bindable_port() -> None:
    port = pick_free_port()
    assert 1024 < port < 65536


def test_wait_until_ready_raises_when_proc_exits_early() -> None:
    # Process thoát ngay -> wait_until_ready phải raise, không treo tới timeout.
    proc = spawn(
        "dummy",
        [sys.executable, "-c", "import sys; print('boom-marker'); sys.exit(1)"],
        cwd=".",
        env={},
    )
    try:
        raised = False
        try:
            wait_until_ready("dummy", "http://127.0.0.1:9/healthz", proc, timeout_s=5.0)
        except RuntimeError as err:
            raised = True
            assert "exited early" in str(err)
            # Đuôi stdout đã bắt được phải xuất hiện trong thông báo lỗi.
            assert "boom-marker" in str(err)
        assert raised
    finally:
        terminate_all([proc])


def test_drain_thread_keeps_chatty_stdout_flowing() -> None:
    # Tiến trình in nhiều hơn buffer pipe OS (~64KB) không được block: daemon
    # drain thread phải rút liên tục, và `tail()` giữ lại phần cuối.
    script = "import sys\nfor i in range(5000): print(f'line-{i}')\nsys.exit(0)"
    proc = spawn("chatty", [sys.executable, "-u", "-c", script], cwd=".", env={})
    try:
        assert proc.popen.wait(timeout=10) == 0
        proc._drain_thread.join(timeout=2.0)
        tail = proc.tail(50)
        assert "line-4999" in tail
        assert "line-0\n" not in tail  # dòng đầu đã bị đẩy khỏi ring buffer
    finally:
        terminate_all([proc])
