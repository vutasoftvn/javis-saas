# backend/app/tests/agents/test_litellm_invoker.py
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest

from app.workforce.agents.reliability.litellm_invoker import cosa_litellm_invoker
from app.workforce.agents.reliability.model_gateway import ModelMessage, ModelRequest


def _fake_litellm_response(content: str, prompt_tokens: int, completion_tokens: int, finish_reason: str = "stop"):
    message = SimpleNamespace(content=content, tool_calls=None)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    usage = SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return SimpleNamespace(choices=[choice], usage=usage)


@pytest.mark.asyncio
async def test_cosa_litellm_invoker_maps_request_and_response(monkeypatch):
    captured: dict = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return _fake_litellm_response("Diagnosis: runway is healthy.", prompt_tokens=42, completion_tokens=8)

    monkeypatch.setattr(
        "app.workforce.agents.reliability.litellm_invoker.litellm.acompletion",
        fake_acompletion,
    )

    request = ModelRequest(
        messages=[ModelMessage(role="user", content="Phân tích runway hiện tại")],
        system_instruction="Bạn là Chief of Staff.",
        temperature=0.3,
        max_tokens=512,
    )
    resp = await cosa_litellm_invoker("deepseek", "deepseek-reasoner", request)

    assert captured["model"] == "deepseek/deepseek-reasoner"
    assert captured["messages"][0] == {"role": "system", "content": "Bạn là Chief of Staff."}
    assert captured["messages"][1] == {"role": "user", "content": "Phân tích runway hiện tại"}
    assert captured["temperature"] == 0.3
    assert captured["max_tokens"] == 512

    assert resp.content == "Diagnosis: runway is healthy."
    assert resp.usage.input_tokens == 42
    assert resp.usage.output_tokens == 8
    assert resp.provider == "deepseek"
    assert resp.model == "deepseek-reasoner"
    assert resp.finish_reason == "stop"
    assert resp.tool_calls == []
