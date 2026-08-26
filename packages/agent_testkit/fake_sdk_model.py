from __future__ import annotations

from agents.models.interface import Model, ModelResponse
from agents.usage import Usage
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText

__all__ = ["FakeSDKModel", "usage", "text_response", "tool_call_response"]


def usage() -> Usage:
    return Usage(input_tokens=10, output_tokens=5, total_tokens=15)


def text_response(text: str) -> ModelResponse:
    return ModelResponse(
        output=[
            ResponseOutputMessage(
                id="msg_1",
                role="assistant",
                status="completed",
                type="message",
                content=[ResponseOutputText(text=text, type="output_text", annotations=[])],
            )
        ],
        usage=usage(),
        response_id="resp_1",
    )


def tool_call_response(call_id: str, tool_name: str, arguments: str = "{}") -> ModelResponse:
    return ModelResponse(
        output=[
            ResponseFunctionToolCall(
                id="fc_1", call_id=call_id, name=tool_name, arguments=arguments, type="function_call", status="completed"
            )
        ],
        usage=usage(),
        response_id="resp_2",
    )


class FakeSDKModel(Model):
    """Model fake điều khiển bằng hàng đợi response, duck-typed đúng
    `agents.models.interface.Model` Protocol — không gọi API thật. Dùng
    trong conformance test của `RealOpenAIAgentsSDKKernel` VÀ trong
    `apps/cosa` integration test (Task 6) để không cần DEEPSEEK_API_KEY."""

    def __init__(self, responses: list[ModelResponse] | None = None, error: Exception | None = None) -> None:
        self._responses = list(responses or [])
        self._error = error
        self.call_count = 0

    async def get_response(self, *args, **kwargs) -> ModelResponse:
        self.call_count += 1
        if self._error:
            raise self._error
        if not self._responses:
            return text_response("no more responses configured")
        return self._responses.pop(0)

    def stream_response(self, *args, **kwargs):  # pragma: no cover - unused ở conformance này
        raise NotImplementedError
