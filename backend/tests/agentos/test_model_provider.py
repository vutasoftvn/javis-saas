import pytest

from agentos.core.model_provider import ModelProvider, ModelResponse, StubModelProvider, ToolCallRequest


def test_stub_model_provider_satisfies_protocol():
    assert isinstance(StubModelProvider([]), ModelProvider)


@pytest.mark.asyncio
async def test_stub_model_provider_replays_responses_in_order():
    provider = StubModelProvider(
        [
            ModelResponse(tool_call=ToolCallRequest(tool_name="echo", arguments={"text": "hi"})),
            ModelResponse(text="done"),
        ]
    )
    first = await provider.generate(system_prompt="p", messages=[])
    second = await provider.generate(system_prompt="p", messages=[])
    assert first.tool_call.tool_name == "echo"
    assert second.text == "done"
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_stub_model_provider_raises_when_exhausted():
    provider = StubModelProvider([])
    with pytest.raises(RuntimeError):
        await provider.generate(system_prompt="p", messages=[])
