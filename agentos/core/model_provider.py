from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict = Field(default_factory=dict)


class TokenUsage(BaseModel):
    """Số token thật do chính API của provider trả về — không bao giờ ước
    lượng/đoán (blueprint §56 yêu cầu cost tracking phải dựa trên usage
    thật từ ModelProvider).
    """

    input_tokens: int
    output_tokens: int


class ModelResponse(BaseModel):
    text: str | None = None
    tool_call: ToolCallRequest | None = None
    model: str | None = None
    usage: TokenUsage | None = None


@runtime_checkable
class ModelProvider(Protocol):
    async def generate(self, *, system_prompt: str, messages: list[dict]) -> ModelResponse:
        ...


class StubModelProvider:
    """Deterministic test double: replays a fixed queue of responses.

    Not a production model — Phase 1 scope is proving the runtime loop
    shape works end-to-end; a real ModelGateway-backed provider (blueprint
    §3.11) is a later phase.
    """

    def __init__(self, responses: list[ModelResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    async def generate(self, *, system_prompt: str, messages: list[dict]) -> ModelResponse:
        self.calls.append({"system_prompt": system_prompt, "messages": messages})
        if not self._responses:
            raise RuntimeError("StubModelProvider ran out of scripted responses")
        return self._responses.pop(0)
