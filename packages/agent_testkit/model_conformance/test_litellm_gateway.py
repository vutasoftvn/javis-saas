"""Conformance test cho LiteLLMModelClient (Wave 4) — verify response pass-through
đúng shape OpenAI-compatible, và exception litellm được map đúng RuntimeErrorCode
thay vì rơi vào MODEL_PROVIDER_ERROR chung chung. Monkeypatch `litellm.acompletion`
để không cần API key/network thật.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

# litellm là dependency của apps/cosa (LiteLLMModelClient qua DeepSeek), không
# thuộc packages/agent/requirements.txt — CI job `agent-core` không cài.
# Skip module thay vì ImportError sập collection (Phase 6 CI Green Gate).
litellm = pytest.importorskip("litellm")

from agent.contracts.errors import AgentRuntimeError, RuntimeErrorCode
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.kernel.openai_agents_kernel import ManualToolLoopKernel
from agent.runs.repository import InMemoryRunRepository
from agent_integrations.litellm.gateway import LiteLLMModelClient


def _fake_response(content: str = "OK") -> SimpleNamespace:
    message = SimpleNamespace(content=content, tool_calls=None)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice], usage=SimpleNamespace(total_tokens=42))


@pytest.mark.asyncio
async def test_litellm_client_passes_through_successful_response(monkeypatch):
    captured = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return _fake_response("Xin chào từ DeepSeek qua LiteLLM")

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    client = LiteLLMModelClient(model="deepseek-chat", fallbacks=["openai/gpt-4o-mini"])
    resp = await client.chat.completions.create(messages=[{"role": "user", "content": "hi"}])

    assert resp.choices[0].message.content == "Xin chào từ DeepSeek qua LiteLLM"
    assert captured["model"] == "deepseek-chat"
    assert captured["fallbacks"] == ["openai/gpt-4o-mini"]


@pytest.mark.asyncio
async def test_litellm_client_maps_rate_limit_error_to_typed_runtime_error(monkeypatch):
    async def fake_acompletion(**kwargs):
        raise litellm.exceptions.RateLimitError(
            message="rate limited", llm_provider="deepseek", model="deepseek-chat"
        )

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    client = LiteLLMModelClient(model="deepseek-chat")
    with pytest.raises(AgentRuntimeError) as exc_info:
        await client.chat.completions.create(messages=[{"role": "user", "content": "hi"}])

    assert exc_info.value.code == RuntimeErrorCode.MODEL_RATE_LIMIT
    assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_kernel_with_litellm_client_surfaces_specific_error_code_not_generic(monkeypatch):
    """Kernel phải giữ nguyên RuntimeErrorCode cụ thể (MODEL_RATE_LIMIT) từ
    LiteLLMModelClient, không re-wrap thành MODEL_PROVIDER_ERROR chung chung
    (fix trong _call_model: `except AgentRuntimeError: raise` trước khi bắt
    Exception rộng)."""

    async def fake_acompletion(**kwargs):
        raise litellm.exceptions.ContextWindowExceededError(
            message="context too long", llm_provider="deepseek", model="deepseek-chat"
        )

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    repo = InMemoryRunRepository()
    client = LiteLLMModelClient(model="deepseek-chat")
    kernel = ManualToolLoopKernel(repository=repo, model_client=client)

    spec = AgentSpec(id="test.litellm.error_code", version="1.0.0")
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "very long context"},
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.FAILED
    run_rec = await repo.get_run(result.run_id)
    assert run_rec.error_details["code"] == RuntimeErrorCode.CONTEXT_LIMIT_EXCEEDED.value
