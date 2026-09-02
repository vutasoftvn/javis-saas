"""Helper spawn/giám sát tiến trình con cho dàn E2E subprocess.

Rút từ pattern đã kiểm chứng ở `tests/e2e/conftest.py::real_company_service`
(pick free port, chờ /healthz chấp nhận 200/503, teardown try/finally).
"""

from __future__ import annotations

import contextlib
import socket
import subprocess
import time
from dataclasses import dataclass

import httpx


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@dataclass
class ManagedProc:
    name: str
    popen: subprocess.Popen


def spawn(name: str, argv: list[str], *, cwd: str, env: dict[str, str]) -> ManagedProc:
    popen = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return ManagedProc(name=name, popen=popen)


def wait_until_ready(
    name: str, health_url: str, proc: ManagedProc, *, timeout_s: float = 60.0
) -> None:
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if proc.popen.poll() is not None:
            output = _drain(proc)
            raise RuntimeError(
                f"[{name}] process exited early with code {proc.popen.returncode} "
                f"before {health_url} became ready.\n--- captured output ---\n{output}"
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
    raise RuntimeError(f"[{name}] not ready within {timeout_s}s: {last_error}")


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


def _drain(proc: ManagedProc) -> str:
    if proc.popen.stdout is None:
        return ""
    with contextlib.suppress(Exception):
        return proc.popen.stdout.read() or ""
    return ""
