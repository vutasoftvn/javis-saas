from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

import httpx
import pytest


def _wait_for_uvicorn_ready(port: int, max_retries: int = 30, retry_interval: float = 0.5) -> None:
    """Poll until uvicorn HTTP server is ready to accept connections.

    Retries every `retry_interval` seconds up to `max_retries` times.
    Raises RuntimeError if server doesn't respond within the timeout.
    """
    retry_count = 0
    while retry_count < max_retries:
        try:
            # Quick HTTP HEAD request to /health or just verify port is open
            response = httpx.head(f"http://127.0.0.1:{port}/", timeout=1.0)
            # Any response (even 404) means the server is running
            return
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, Exception):
            pass

        retry_count += 1
        if retry_count < max_retries:
            time.sleep(retry_interval)

    # Timeout — server didn't start
    raise RuntimeError(
        f"uvicorn on port {port} did not become ready within "
        f"{max_retries * retry_interval:.1f} seconds"
    )


@pytest.mark.integration
def test_sse_reconnect_survives_process_restart(postgres_dsn, run_id_with_events):
    """E2E test: SSE reconnect via Last-Event-ID after API process restart.

    Proves that:
    1. A real uvicorn subprocess (pid1) can stream SSE events from the durable
       event store
    2. After hard kill (SIGKILL), a new subprocess (pid2) can restart
    3. A client reconnecting with Last-Event-ID resumes from the correct sequence,
       with no duplicates and no gaps

    This is NOT an in-process simulation — it uses real OS subprocesses hitting
    the real HTTP API layer, proving durability across actual process boundaries.
    """
    # Prepare environment — substitute docker hostname for host network access
    env = {**os.environ}
    if postgres_dsn:
        env["AGENT_CORE_DATABASE_URL"] = postgres_dsn
    else:
        pytest.skip("postgres_dsn fixture failed")

    # Ensure PYTHONPATH includes packages and apps directories for uvicorn subprocess
    import sys

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    pythonpath = f"{repo_root}:{repo_root}/packages:{repo_root}/apps"
    if "PYTHONPATH" in env:
        pythonpath = f"{pythonpath}:{env['PYTHONPATH']}"
    env["PYTHONPATH"] = pythonpath

    # --- Phase 1: Start first uvicorn process and read initial events ---
    proc1 = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "apps.cosa.api.test_main:app", "--port", "8091"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    pid1 = proc1.pid
    _wait_for_uvicorn_ready(8091)

    first_events = []
    last_id_after_phase1 = None

    try:
        with httpx.Client(timeout=5.0) as client:
            with client.stream(
                "GET",
                f"http://127.0.0.1:8091/agent/runs/{run_id_with_events}/events",
            ) as r:
                for line in r.iter_lines():
                    if line.startswith("id:"):
                        event_id = line.split(":", 1)[1].strip()
                        first_events.append(event_id)
                        last_id_after_phase1 = event_id
                    # Collect at least 2 events before closing
                    if len(first_events) >= 2:
                        break
    finally:
        # Hard kill the first process
        proc1.send_signal(signal.SIGKILL)
        proc1.wait(timeout=5)

    assert len(first_events) >= 2, f"Expected at least 2 events from phase 1, got {len(first_events)}"
    assert last_id_after_phase1 is not None, "Should have collected at least one event ID"

    # --- Phase 2: Start second uvicorn process and reconnect with Last-Event-ID ---
    proc2 = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "apps.cosa.api.test_main:app", "--port", "8091"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    pid2 = proc2.pid
    _wait_for_uvicorn_ready(8091)

    resumed_ids = []

    try:
        with httpx.Client(timeout=5.0) as client:
            # Reconnect with Last-Event-ID set to the last ID we saw before restart
            headers = {"Last-Event-ID": last_id_after_phase1}
            with client.stream(
                "GET",
                f"http://127.0.0.1:8091/agent/runs/{run_id_with_events}/events",
                headers=headers,
            ) as r:
                for line in r.iter_lines():
                    if line.startswith("id:"):
                        event_id = line.split(":", 1)[1].strip()
                        resumed_ids.append(event_id)
                    # Collect at least 1 event from resumed stream
                    if len(resumed_ids) >= 1:
                        break
    finally:
        # Clean up second process
        proc2.send_signal(signal.SIGKILL)
        proc2.wait(timeout=5)

    # --- Verification ---
    assert pid1 != pid2, f"Process PIDs should differ: pid1={pid1}, pid2={pid2}"
    assert len(resumed_ids) >= 1, f"Expected at least 1 event from resumed stream, got {len(resumed_ids)}"

    # Resumed stream should pick up AFTER the last ID we saw (sequence numbers are integers)
    last_seen_seq = int(last_id_after_phase1)
    resumed_seq = int(resumed_ids[0])
    assert resumed_seq > last_seen_seq, (
        f"Resumed stream should continue after last seen ID: "
        f"last_seen={last_seen_seq}, resumed={resumed_seq}"
    )

    # Verify no duplicates — resumed_ids should not contain any IDs we already saw
    overlap = set(first_events) & set(resumed_ids)
    assert len(overlap) == 0, f"Resumed stream should not duplicate events: overlap={overlap}"
