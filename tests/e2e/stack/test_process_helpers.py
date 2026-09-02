"""Test helper tiến trình — không cần service thật, chỉ spawn `python -c`."""

from __future__ import annotations

import sys

from tests.e2e.stack._process import pick_free_port, spawn, terminate_all, wait_until_ready


def test_pick_free_port_returns_bindable_port() -> None:
    port = pick_free_port()
    assert 1024 < port < 65536


def test_wait_until_ready_raises_when_proc_exits_early() -> None:
    # Process thoát ngay -> wait_until_ready phải raise, không treo tới timeout.
    proc = spawn("dummy", [sys.executable, "-c", "raise SystemExit(1)"], cwd=".", env={})
    try:
        raised = False
        try:
            wait_until_ready("dummy", "http://127.0.0.1:9/healthz", proc, timeout_s=5.0)
        except RuntimeError as err:
            raised = True
            assert "exited early" in str(err)
        assert raised
    finally:
        terminate_all([proc])
