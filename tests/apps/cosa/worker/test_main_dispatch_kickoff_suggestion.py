from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from apps.cosa.worker import main as worker_main


@pytest.mark.asyncio
async def test_dispatch_one_task_routes_kickoff_suggestion(monkeypatch):
    task = SimpleNamespace(task_id="t1", claim_token="claim1", input_payload={
        "task_type": "kickoff_suggestion",
        "run_id": "run1",
        "workspace_id": "ws1",
        "project_id": "p1",
    })
    scheduler = AsyncMock()
    scheduler.complete_task.return_value = True
    plane = SimpleNamespace(scheduler=scheduler)

    with patch(
        "apps.cosa.worker.kickoff_suggestion_run.execute_kickoff_suggestion_task", new=AsyncMock()
    ) as exec_mock:
        await worker_main.dispatch_one_task(plane, task)

    exec_mock.assert_awaited_once()
    scheduler.complete_task.assert_awaited_once()
    assert scheduler.complete_task.call_args.kwargs["success"] is True
