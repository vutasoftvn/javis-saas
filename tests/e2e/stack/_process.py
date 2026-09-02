"""Helper spawn/giám sát tiến trình con cho dàn E2E subprocess.

Rút từ pattern đã kiểm chứng ở `tests/e2e/conftest.py::real_company_service`
(pick free port, chờ /healthz chấp nhận 200/503, teardown try/finally).

Bổ sung Task 5: mỗi tiến trình con có một daemon thread liên tục đọc
`popen.stdout` vào một ring buffer trong bộ nhớ. `encore run` in log RẤT nhiều
lúc khởi động; nếu không ai rút pipe, buffer ~64KB của OS đầy và tiến trình con
bị chặn ở lệnh write → stack không bao giờ healthy và ta nhận timeout gây hiểu
lầm. Ring buffer giữ lại phần đuôi log để chẩn đoán khi tiến trình chết hoặc
health check timeout.
"""

from __future__ import annotations

import contextlib
import socket
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field

import httpx

# Giữ tối đa ngần này dòng stdout mỗi tiến trình — đủ để đọc nguyên nhân crash
# lúc boot mà không giữ toàn bộ log Encore (hàng chục nghìn dòng) trong RAM.
_RING_BUFFER_LINES = 4000


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@dataclass
class ManagedProc:
    name: str
    popen: subprocess.Popen
    # Ring buffer + thread rút pipe: field private, không truyền qua ctor.
    _lines: deque[str] = field(default_factory=lambda: deque(maxlen=_RING_BUFFER_LINES))
    _drain_thread: threading.Thread | None = None

    def tail(self, n: int = 200) -> str:
        """Trả về tối đa `n` dòng stdout gần nhất đã bắt được."""
        return "".join(list(self._lines)[-n:])


def _drain_loop(proc: ManagedProc) -> None:
    stdout = proc.popen.stdout
    if stdout is None:
        return
    # `iter(readline, "")` chạy tới khi pipe EOF (tiến trình con đóng stdout).
    with contextlib.suppress(Exception):
        for line in iter(stdout.readline, ""):
            proc._lines.append(line)


def spawn(name: str, argv: list[str], *, cwd: str, env: dict[str, str]) -> ManagedProc:
    popen = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    proc = ManagedProc(name=name, popen=popen)
    thread = threading.Thread(target=_drain_loop, args=(proc,), name=f"drain-{name}", daemon=True)
    proc._drain_thread = thread
    thread.start()
    return proc


def wait_until_ready(
    name: str, health_url: str, proc: ManagedProc, *, timeout_s: float = 60.0
) -> None:
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if proc.popen.poll() is not None:
            # Cho drain thread một nhịp để flush nốt phần đuôi trước khi in.
            if proc._drain_thread is not None:
                proc._drain_thread.join(timeout=2.0)
            raise RuntimeError(
                f"[{name}] process exited early with code {proc.popen.returncode} "
                f"before {health_url} became ready.\n--- captured stdout tail ---\n{proc.tail()}"
            )
        try:
            resp = httpx.get(health_url, timeout=2.0)
            # 503 = app đã lên nhưng probe DB nội bộ của /healthz đỏ; với fixture
            # này DB đã verify riêng, coi như "đã nhận request được".
            if resp.status_code in (200, 503):
                return
        except httpx.HTTPError as err:
            last_error = err
        time.sleep(0.5)
    raise RuntimeError(
        f"[{name}] not ready within {timeout_s}s: {last_error}\n"
        f"--- captured stdout tail ---\n{proc.tail()}"
    )


def terminate_all(procs: list[ManagedProc]) -> None:
    for proc in reversed(procs):
        if proc.popen.poll() is None:
            proc.popen.terminate()
            try:
                proc.popen.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.popen.kill()
                with contextlib.suppress(Exception):
                    proc.popen.wait(timeout=15)
        if proc._drain_thread is not None:
            proc._drain_thread.join(timeout=2.0)
