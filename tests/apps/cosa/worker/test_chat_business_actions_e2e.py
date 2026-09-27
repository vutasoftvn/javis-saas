"""Tích hợp đầy đủ trong process (plane thật, kernel SDK thật, gateway thật, model giả) cho spec
2026-09-27-chat-business-actions: chat đọc OKR qua business.read → đề xuất tạo Key Result →
run chờ founder duyệt (thẻ có tóm tắt bằng tên) → duyệt: handler company gọi đúng một lần →
từ chối: handler không bao giờ được gọi → lỗi 401 của một tool không làm hỏng run → T3 không
phải tool của chat. Khẳng định bằng số lần gọi mock client, không bằng văn bản của model."""

from __future__ import annotations

from typing import Any

import pytest
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response, tool_call_response

from apps.cosa.agents.seed import seed_cosa_runtime_specs
from apps.cosa.agents.specs import COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.capabilities.client import CompanyServiceError
from apps.cosa.worker.handlers import execute_resume_task, execute_run_task
from tests.apps.cosa.worker.test_handlers import _payload, _plane

KR_ARGS = '{"objective_id": "obj-42", "title": "MRR 1 tỷ", "target_value": 1000000000}'


def _company_get(path: str, *args: Any, **kwargs: Any) -> Any:
    if path == "/operations/objectives":
        return {"data": [{"id": "obj-42", "title": "Tăng trưởng doanh thu", "status": "published"}]}
    if path == "/operations/key-results":
        return {"data": []}
    raise AssertionError(f"unexpected GET {path}")


async def _plane_with(responses: list[Any]) -> Any:
    plane = _plane()
    plane.kernel._model = FakeSDKModel(responses=responses)
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry, capability_registry=plane.capability_registry
    )
    company = plane.company_client
    company.get.side_effect = _company_get
    company.post.return_value = {"id": "kr-new", "title": "MRR 1 tỷ", "status": "draft"}
    return plane


def _kr_posts(plane: Any) -> list[Any]:
    return [
        c
        for c in plane.company_client.post.await_args_list
        if str(c.args[0]).endswith("/key-results")
    ]


async def _events(plane: Any, run_id: str, event_type: str) -> list[dict]:
    events = await plane.stream_event_repository.list_since(run_id)
    return [e.payload for e in events if e.event_type == event_type]


async def _start_until_approval(plane: Any, run_id: str) -> dict:
    await execute_run_task(
        plane,
        CosaEventStreamManager(),
        _payload(
            run_id=run_id, user_prompt="căn cứ OKR hãy tạo Key Result", project_name="Sao Mai"
        ),
    )
    [required] = await _events(plane, run_id, "approval.required")
    return required


def _resume_payload(plane: Any, run_id: str, required: dict, *, decision: str) -> dict:
    return {
        "run_id": run_id,
        "checkpoint_ref": required["checkpoint_ref"],
        "conversation_id": "conv_1",
        "workspace_id": "ws_1",
        "project_id": "proj_1",
        "delegation_token": "fake-token",
        "tool_call_id": "call_kr",
        "approval_id": required["approval_id"],
        "decision": decision,
    }


@pytest.mark.asyncio
async def test_read_propose_approve_executes_exactly_once() -> None:
    run_id = "run_e2e_approve"
    plane = await _plane_with(
        [
            tool_call_response("call_read", "business.read", '{"domain": "okr"}'),
            tool_call_response("call_kr", "okr.key_result.create", KR_ARGS),
            text_response("Đã tạo Key Result MRR 1 tỷ cho mục tiêu Tăng trưởng doanh thu."),
        ]
    )

    required = await _start_until_approval(plane, run_id)

    # business.read đọc OKR thật qua capability đích; chưa có ghi nào trước khi duyệt.
    get_paths = [c.args[0] for c in plane.company_client.get.await_args_list]
    assert "/operations/objectives" in get_paths
    assert _kr_posts(plane) == []
    assert required["capability_id"] == "okr.key_result.create" and required["tier"] == "T2"
    assert required["summary"]["title"] == "Tạo Key Result mới cho Sao Mai"
    assert "obj-42" not in str(required["summary"])

    await plane.approval_service.submit_decision(
        approval_id=required["approval_id"], reviewer="user_1", approved=True, reason=""
    )
    await execute_resume_task(
        plane,
        CosaEventStreamManager(),
        _resume_payload(plane, run_id, required, decision="approved"),
    )

    # Ghi thật đi qua live authorization ticket của company bằng AI member của Project team.
    [ticket] = [
        c
        for c in plane.company_client.post.await_args_list
        if c.args[0] == "/identity/agent-authorization/tickets"
    ]
    assert ticket.kwargs["json"]["capabilityId"] == "okr.key_result.create"
    assert ticket.kwargs["json"]["agentWorkforceMemberId"] == "wm_mock_1"
    [post] = _kr_posts(plane)
    assert post.args[0] == "/operations/objectives/obj-42/key-results"
    assert post.kwargs["json"]["title"] == "MRR 1 tỷ"
    assert await _events(plane, run_id, "run.completed")


@pytest.mark.asyncio
async def test_reject_never_calls_the_write_handler_and_agent_continues() -> None:
    run_id = "run_e2e_reject"
    plane = await _plane_with(
        [
            tool_call_response("call_kr", "okr.key_result.create", KR_ARGS),
            text_response("Đã hiểu, tôi sẽ không tạo Key Result này."),
        ]
    )

    required = await _start_until_approval(plane, run_id)
    await plane.approval_service.submit_decision(
        approval_id=required["approval_id"], reviewer="user_1", approved=False, reason="không"
    )
    await execute_resume_task(
        plane,
        CosaEventStreamManager(),
        _resume_payload(plane, run_id, required, decision="rejected"),
    )

    assert _kr_posts(plane) == []
    assert await _events(plane, run_id, "run.completed")


@pytest.mark.asyncio
async def test_backend_401_on_a_read_tool_does_not_fail_the_chat_run() -> None:
    run_id = "run_e2e_401"
    plane = await _plane_with(
        [
            tool_call_response("call_nba", "strategy.next_best_action.get", "{}"),
            text_response("Tôi chưa lấy được việc nên làm tiếp theo, đây là phần còn lại."),
        ]
    )
    plane.company_client.get.side_effect = CompanyServiceError(
        "Company Service Error (401): invalid token", status_code=401
    )

    await execute_run_task(plane, CosaEventStreamManager(), _payload(run_id=run_id))

    assert plane.company_client.get.await_count == 1
    assert await _events(plane, run_id, "run.completed")
    assert not await _events(plane, run_id, "run.failed")


def test_t3_capabilities_are_not_tools_of_the_chat_spec() -> None:
    for cap in ("engagement.message.send", "finance.accounting_document.confirm"):
        assert cap not in COSA_OPERATIONS_AGENT_SPEC.capability_refs
