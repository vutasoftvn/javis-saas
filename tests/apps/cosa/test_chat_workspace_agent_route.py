"""C1 — route chat chuyển `project_agent_deployment_id` (tuỳ chọn) vào payload run.

Route không tự tin tham chiếu này; worker kiểm lại với company
(tests/apps/cosa/worker/test_agent_clone_executor_e2e.py).
"""

from __future__ import annotations

import httpx
import pytest

from tests.apps.cosa.test_conversation_locale import (  # noqa: F401 — fixture dùng lại
    queued_payload,
    test_setup,
    valid_access,
)


async def _send(app, extra: dict) -> dict:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        conv = await client.post(
            "/agent/conversations",
            json={
                "title": "Agent riêng",
                "active_agent_profile": "operations",
                "project_id": "proj_locale_1",
            },
        )
        res = await client.post(
            f"/agent/conversations/{conv.json()['id']}/messages",
            json={
                "content": "Liệt kê việc tuần này",
                "role": "user",
                "project_id": "proj_locale_1",
                "data_access": valid_access(),
                **extra,
            },
        )
        assert res.status_code == 202
        return res.json()


@pytest.mark.asyncio
async def test_deployment_id_is_forwarded_to_the_run_payload(test_setup):  # noqa: F811
    app, plane, _ = test_setup
    body = await _send(app, {"project_agent_deployment_id": "dep_custom_1"})
    assert queued_payload(plane, body["run_id"])["project_agent_deployment_id"] == "dep_custom_1"


@pytest.mark.asyncio
async def test_without_deployment_id_the_payload_is_unchanged(test_setup):  # noqa: F811
    app, plane, _ = test_setup
    body = await _send(app, {})
    assert "project_agent_deployment_id" not in queued_payload(plane, body["run_id"])
