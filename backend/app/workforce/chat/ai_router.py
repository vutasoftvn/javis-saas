from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Literal, Protocol


@dataclass(frozen=True)
class ToolCall:
    """Một lần model xin gọi tool. ``arguments`` giữ nguyên chuỗi JSON model sinh ra -
    chỉ parse ở nơi thực thi, để lỗi JSON hỏng là lỗi của một tool chứ không làm chết lượt."""

    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class ChatTurn:
    role: str
    content: str
    # Lượt "assistant" mang tool_calls và lượt "tool" mang tool_call_id là bắt buộc phải
    # phát lại nguyên vẹn ở vòng sau, nếu không provider từ chối cả hội thoại.
    tool_calls: tuple[ToolCall, ...] | None = None
    tool_call_id: str | None = None


@dataclass(frozen=True)
class AIEvent:
    kind: Literal["delta", "completed", "failed", "tool_call"]
    content: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    error_code: str | None = None
    tool_call: ToolCall | None = None


class ChatProvider(Protocol):
    def stream_chat(
        self, turns: list[ChatTurn], tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[AIEvent]: ...


# (provider_name, model, workspace_id) -> instance sẵn sàng gọi .stream_chat().
# Xem app/modules/chat/providers.py.
ProviderFactory = Callable[[str, str, int | None], ChatProvider]


class AIRouter:
    """Chọn đúng ChatProvider theo (provider, model) của từng chat session thay vì gắn
    cứng 1 provider - mỗi cuộc hội thoại có thể dùng model khác nhau (Wave 1: model
    picker). `factory` ném ValueError nếu provider không được hỗ trợ; lỗi này cố tình
    không bị nuốt ở đây để chat_execution_service ghi nhận đúng error_code."""

    def __init__(self, factory: ProviderFactory):
        self._factory = factory

    def stream_chat(
        self,
        turns: list[ChatTurn],
        provider: str,
        model: str,
        tools: list[dict[str, Any]] | None = None,
        workspace_id: int | None = None,
    ) -> AsyncIterator[AIEvent]:
        return self._factory(provider, model, workspace_id).stream_chat(turns, tools=tools)
