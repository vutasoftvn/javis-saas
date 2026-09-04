from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from agent.contracts.run import RunStatus
from apps.cosa.worker import kickoff_suggestion_run


def _run_result(status, final_output="", errors=None):
    return SimpleNamespace(
        status=status, final_output=final_output, errors=errors or [], interruptions_waits=[]
    )


def _plane(*, kernel_result):
    kernel = AsyncMock()
    kernel.run.return_value = kernel_result
    resolver = AsyncMock()
    resolver.resolve_for_run.return_value = {"_company_delegation_token": "jwt-x"}
    return SimpleNamespace(
        kernel=kernel,
        compliance_resolver=resolver,
        spec_registry=SimpleNamespace(),
    )


@pytest.fixture(autouse=True)
def _patch_resolve_spec(monkeypatch):
    async def _fake_resolve_spec(plane, *, run_id, local_spec):
        return SimpleNamespace(
            to_pinned_identity=lambda: "cosa.agents.operations@1.2.0#h",
            spec_id="cosa.agents.operations",
        )

    monkeypatch.setattr("apps.cosa.worker.run_core.resolve_spec", _fake_resolve_spec)
    monkeypatch.setenv("COSA_COMPANY_DELEGATION_SECRET", "x" * 40)


_VALID_OUTPUT = json.dumps(
    {
        "outcome": "Hoàn thành 5 cuộc phỏng vấn khách hàng mục tiêu",
        "actions": ["Phỏng vấn 5 khách hàng mục tiêu", "Ghi chép pain point"],
    }
)

_PAYLOAD = {
    "run_id": "kickoff_sugg_1",
    "workspace_id": "ws1",
    "project_id": "proj1",
    "target_customer": "Founder B2B SaaS",
    "problem_statement": "Không biết validate ý tưởng",
    "evidence_level": "NONE",
    "selected_stage": "P0_DISCOVERY",
    "stage_duration_weeks": 2,
}


@pytest.mark.asyncio
async def test_execute_task_callbacks_completed_on_valid_output():
    plane = _plane(kernel_result=_run_result(RunStatus.COMPLETED, {"response": _VALID_OUTPUT}))

    with patch.object(kickoff_suggestion_run, "callback_kickoff_result", new=AsyncMock()) as cb:
        await kickoff_suggestion_run.execute_kickoff_suggestion_task(plane, None, _PAYLOAD)

    cb.assert_awaited_once_with(
        "proj1",
        "kickoff_sugg_1",
        "completed",
        outcome="Hoàn thành 5 cuộc phỏng vấn khách hàng mục tiêu",
        actions=["Phỏng vấn 5 khách hàng mục tiêu", "Ghi chép pain point"],
    )
    # Không capability nào được gọi — plane không có capability_registry trong
    # fixture này, nên bất kỳ truy cập nào vào nó sẽ tự raise AttributeError
    # và làm test fail nếu code lỡ gọi capability.


@pytest.mark.asyncio
async def test_execute_task_callbacks_failed_on_invalid_schema():
    plane = _plane(kernel_result=_run_result(RunStatus.COMPLETED, {"response": "not json"}))

    with patch.object(kickoff_suggestion_run, "callback_kickoff_result", new=AsyncMock()) as cb:
        await kickoff_suggestion_run.execute_kickoff_suggestion_task(plane, None, _PAYLOAD)

    cb.assert_awaited_once_with("proj1", "kickoff_sugg_1", "failed")


@pytest.mark.asyncio
async def test_execute_task_callbacks_failed_on_kernel_non_completed():
    plane = _plane(kernel_result=_run_result(RunStatus.FAILED, errors=["boom"]))

    with patch.object(kickoff_suggestion_run, "callback_kickoff_result", new=AsyncMock()) as cb:
        await kickoff_suggestion_run.execute_kickoff_suggestion_task(plane, None, _PAYLOAD)

    cb.assert_awaited_once_with("proj1", "kickoff_sugg_1", "failed")


@pytest.mark.asyncio
async def test_callback_kickoff_result_posts_to_company(monkeypatch):
    monkeypatch.setenv("COMPANY_SERVICE_URL", "http://127.0.0.1:4000")
    monkeypatch.setenv("COSA_SERVICE_TOKEN", "test-token-" + "x" * 30)

    captured = {}

    class _FakeResponse:
        status_code = 200

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _FakeResponse()

    with patch("apps.cosa.worker.kickoff_suggestion_run.httpx.AsyncClient", _FakeAsyncClient):
        await kickoff_suggestion_run.callback_kickoff_result(
            "proj1", "run1", "completed", outcome="x", actions=["y"]
        )

    assert captured["url"] == "http://127.0.0.1:4000/operations/projects/proj1/kickoff-suggestion/result"
    assert captured["json"] == {"runId": "run1", "status": "completed", "outcome": "x", "actions": ["y"]}
    assert captured["headers"]["X-Cosa-Service-Token"] == "test-token-" + "x" * 30
