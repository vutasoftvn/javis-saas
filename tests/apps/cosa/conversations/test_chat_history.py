"""ADR-CONV-002 — chat nhớ các lượt trước."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("agents")

from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import ExecutionMode
from agent.runs.repository import InMemoryRunRepository
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response

from apps.cosa.conversations.history import build_history


def _m(role: str, content: str, *, run_id: str | None = None, status: str = "completed"):
    return SimpleNamespace(role=role, content=content, run_id=run_id, status=status)


def test_build_history_keeps_recent_turns_in_order_and_skips_current_and_failed():
    msgs = [
        _m("user", "Mình đang làm SaaS kế toán cho SME", run_id="r1"),
        _m("assistant", "Ghi nhận: SaaS kế toán, khách hàng SME.", run_id="r1"),
        _m("assistant", "lỗi provider", run_id="r2", status="failed"),
        _m("user", "Runway còn 6 tháng", run_id="r3"),
        _m("user", "Vậy nên ưu tiên gì?", run_id="r_now"),
    ]
    h = build_history(msgs, exclude_run_id="r_now", max_messages=10, max_chars=10_000)
    assert h == [
        {"role": "user", "content": "Mình đang làm SaaS kế toán cho SME"},
        {"role": "assistant", "content": "Ghi nhận: SaaS kế toán, khách hàng SME."},
        {"role": "user", "content": "Runway còn 6 tháng"},
    ]


def test_build_history_budget_drops_oldest_first():
    msgs = [_m("user", f"m{i}" * 10) for i in range(6)]
    h = build_history(msgs, exclude_run_id=None, max_messages=2, max_chars=10_000)
    assert [x["content"] for x in h] == ["m4" * 10, "m5" * 10]
    h2 = build_history(msgs, exclude_run_id=None, max_messages=10, max_chars=45)
    assert [x["content"] for x in h2] == ["m4" * 10, "m5" * 10]
    assert build_history(msgs, exclude_run_id=None, max_messages=0, max_chars=100) == []


def test_structured_agent_cards_become_short_descriptions():
    msgs = [
        _m("assistant", '{"kind":"goal_confirm","normalized_goal":"Chốt 3 phỏng vấn"}'),
        _m("assistant", '{"kind":"plan_progress","plan_id":"p","done":["A"],"blocked":["B"]}'),
    ]
    h = build_history(msgs, exclude_run_id=None, max_messages=10, max_chars=10_000)
    assert h[0]["content"] == "[Đã đề xuất đặt mục tiêu tuần: Chốt 3 phỏng vấn]"
    assert "xong: A" in h[1]["content"] and "bị chặn: B" in h[1]["content"]
    assert "{" not in h[1]["content"]


class _RecordingModel(FakeSDKModel):
    def __init__(self) -> None:
        super().__init__(responses=[text_response("Ưu tiên kéo dài runway.")])
        self.inputs: list[Any] = []

    async def get_response(self, *args, **kwargs):
        self.inputs.append(kwargs.get("input", args[1] if len(args) > 1 else None))
        return await super().get_response(*args, **kwargs)


@pytest.mark.asyncio
async def test_sdk_kernel_sends_previous_turns_to_the_model():
    model = _RecordingModel()
    kernel = RealOpenAIAgentsSDKKernel(
        repository=InMemoryRunRepository(),
        capability_registry=CapabilityRegistry(),
        capability_executor=None,
        model=model,
        policy_evaluator=lambda *a, **k: "ALLOW",
    )
    spec = AgentSpec(
        id="history_agent",
        version="1.0.0",
        instructions="Co-founder.",
        capability_refs=[],
        model_input_capability_ref="model.input.direct-user-message",
    ).with_hash()
    req = RunRequest(
        input={
            "prompt": "Vậy nên ưu tiên gì?",
            "history": [
                {"role": "user", "content": "Runway còn 6 tháng"},
                {"role": "assistant", "content": "Ghi nhận runway 6 tháng."},
            ],
        },
        principal="user:1",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws1",
    )
    res = await kernel.run(req, spec)
    assert res.status == RunStatus.COMPLETED
    sent = model.inputs[0]
    assert isinstance(sent, list)
    texts = [str(i.get("content")) for i in sent if isinstance(i, dict)]
    assert texts[:2] == ["Runway còn 6 tháng", "Ghi nhận runway 6 tháng."]
    assert texts[-1] == "Vậy nên ưu tiên gì?"


@pytest.mark.asyncio
async def test_worker_loads_history_from_conversation_repository(monkeypatch):
    from agent.conversations.models import ConversationRecord, MessageRecord
    from agent.conversations.repository import InMemoryConversationRepository

    from apps.cosa.worker.handlers import _load_chat_history

    repo = InMemoryConversationRepository()
    conv = await repo.create_conversation(
        ConversationRecord(
            workspace_id="ws1",
            title="t",
            project_id="p1",
            scope_state="PROJECT_SCOPED",
            created_by_principal="user:1",
        )
    )
    for role, content, run in (
        ("user", "Lượt 1", "run_1"),
        ("assistant", "Trả lời 1", "run_1"),
        ("user", "Lượt 2 (hiện tại)", "run_2"),
    ):
        await repo.add_message(
            MessageRecord(
                conversation_id=conv.conversation_id,
                project_id="p1",
                role=role,
                content=content,
                run_id=run,
                status="completed",
            )
        )
    plane = SimpleNamespace(conversation_repository=repo)

    h = await _load_chat_history(plane, conversation_id=conv.conversation_id, run_id="run_2")
    assert [x["content"] for x in h] == ["Lượt 1", "Trả lời 1"]

    monkeypatch.setenv("COSA_CHAT_HISTORY_MESSAGES", "0")
    assert (
        await _load_chat_history(plane, conversation_id=conv.conversation_id, run_id="run_2") == []
    )
