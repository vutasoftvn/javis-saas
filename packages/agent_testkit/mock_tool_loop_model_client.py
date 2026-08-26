from __future__ import annotations

import json
import uuid
from typing import Any

__all__ = ["MockToolLoopModelClient"]


class _FakeUsage:
    def __init__(self, total_tokens: int) -> None:
        self.total_tokens = total_tokens


class _FakeFunction:
    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class _FakeToolCall:
    def __init__(self, call_id: str, name: str, arguments: str) -> None:
        self.id = call_id
        self.function = _FakeFunction(name, arguments)


class _FakeMessage:
    def __init__(self, content: str, tool_calls: list[_FakeToolCall]) -> None:
        self.content = content
        self.tool_calls = tool_calls


class _FakeChoice:
    def __init__(self, message: _FakeMessage) -> None:
        self.message = message


class _FakeResponse:
    def __init__(self, choices: list[_FakeChoice], usage: _FakeUsage | None) -> None:
        self.choices = choices
        self.usage = usage


class _MockCompletions:
    async def create(
        self, *, model: str, messages: list[dict[str, Any]], temperature: float = 0.0, **kwargs: Any
    ) -> _FakeResponse:
        has_tool_message = any(m.get("role") == "tool" for m in messages)
        if has_tool_message:
            return _FakeResponse(
                choices=[
                    _FakeChoice(
                        _FakeMessage(
                            f"Completed execution after tool call: {messages[-1].get('content')}", []
                        )
                    )
                ],
                usage=_FakeUsage(50),
            )

        last_msg = messages[-1]["content"] if messages else ""
        lower = last_msg.lower()

        if "task" in lower or "operations" in lower:
            tc = _FakeToolCall(
                f"call_{uuid.uuid4().hex[:8]}",
                "operations.task.list",
                json.dumps({"workspace_id": 1, "status": "in_progress"}),
            )
            return _FakeResponse(
                choices=[_FakeChoice(_FakeMessage("Listing operations tasks.", [tc]))], usage=None
            )

        if "payout" in lower or "wire" in lower or "transfer" in lower or "pay" in lower:
            tc = _FakeToolCall(
                f"call_{uuid.uuid4().hex[:8]}",
                "finance.payout.execute",
                json.dumps(
                    {
                        "amount": 20000,
                        "vendor": "Acme Corp",
                        "currency": "USD",
                        "idempotency_key": "idem_slice2",
                    }
                ),
            )
            return _FakeResponse(
                choices=[_FakeChoice(_FakeMessage("Initiating transfer request.", [tc]))], usage=None
            )

        if "weather" in lower:
            tc = _FakeToolCall(f"call_{uuid.uuid4().hex[:8]}", "weather.get", json.dumps({"city": "Hanoi"}))
            return _FakeResponse(
                choices=[_FakeChoice(_FakeMessage("Checking weather.", [tc]))], usage=None
            )

        return _FakeResponse(
            choices=[_FakeChoice(_FakeMessage(f"Processed: {last_msg}", []))], usage=_FakeUsage(100)
        )


class _MockChat:
    def __init__(self) -> None:
        self.completions = _MockCompletions()


class MockToolLoopModelClient:
    """Test double thay cho model provider thật — cùng interface
    `.chat.completions.create(...)` mà `ManualToolLoopKernel` mong đợi từ
    client thật (OpenAI/DeepSeek/LiteLLM), để test kernel mà không cần API
    key thật.

    Logic branching theo keyword trong last user message được chuyển NGUYÊN
    VẸN từ nhánh mock cũ trong `ManualToolLoopKernel._call_model()` — nhánh
    đó bị xoá khỏi production path vì production giờ PHẢI raise nếu thiếu
    model_client thật, không còn silent mock fallback
    (COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §3.2)."""

    @property
    def chat(self) -> _MockChat:
        return _MockChat()
