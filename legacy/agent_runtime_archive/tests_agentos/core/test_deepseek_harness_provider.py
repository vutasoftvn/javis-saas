from __future__ import annotations

import sys
import types

import pytest

from agentos.core.adapters.deepseek_harness_provider import (
    DeepSeekHarnessModelProvider,
    DeepSeekHarnessUnavailableError,
)


@pytest.mark.asyncio
async def test_generate_raises_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    provider = DeepSeekHarnessModelProvider(api_key=None)

    with pytest.raises(DeepSeekHarnessUnavailableError, match="DEEPSEEK_API_KEY"):
        await provider.generate(system_prompt="sys", messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_generate_raises_when_sdk_not_installed(monkeypatch):
    monkeypatch.delitem(sys.modules, "deepseek_harness", raising=False)
    monkeypatch.setattr(
        "agentos.core.adapters.deepseek_harness_provider.DeepSeekHarnessModelProvider._import_sdk",
        lambda self: (_ for _ in ()).throw(
            DeepSeekHarnessUnavailableError("deepseek-harness-sdk chưa được cài đặt")
        ),
    )
    provider = DeepSeekHarnessModelProvider(api_key="test-key")

    with pytest.raises(DeepSeekHarnessUnavailableError, match="chưa được cài đặt"):
        await provider.generate(system_prompt="sys", messages=[{"role": "user", "content": "hi"}])


def _install_fake_sdk(monkeypatch, final_response: str):
    class FakeHarness:
        def __init__(self, config):
            self.config = config
            self.started = False
            self.closed = False

        def start(self):
            self.started = True

        def run(self, task: str):
            assert self.started
            return types.SimpleNamespace(final_response=final_response, finish_reason="completed")

        def close(self):
            self.closed = True

    class FakeConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    fake_module = types.ModuleType("deepseek_harness")
    fake_module.DeepSeekHarness = FakeHarness
    fake_module.DeepSeekHarnessConfig = FakeConfig
    monkeypatch.setitem(sys.modules, "deepseek_harness", fake_module)


@pytest.mark.asyncio
async def test_generate_returns_text_for_plain_response(monkeypatch):
    _install_fake_sdk(monkeypatch, final_response="Hello from the harness")
    provider = DeepSeekHarnessModelProvider(api_key="test-key")

    response = await provider.generate(system_prompt="sys", messages=[{"role": "user", "content": "hi"}])

    assert response.text == "Hello from the harness"
    assert response.tool_call is None


@pytest.mark.asyncio
async def test_generate_parses_tool_call_convention(monkeypatch):
    _install_fake_sdk(
        monkeypatch,
        final_response='{"tool_call": {"name": "task_create", "arguments": {"title": "Ship it"}}}',
    )
    provider = DeepSeekHarnessModelProvider(api_key="test-key")

    response = await provider.generate(system_prompt="sys", messages=[{"role": "user", "content": "hi"}])

    assert response.text is None
    assert response.tool_call is not None
    assert response.tool_call.tool_name == "task_create"
    assert response.tool_call.arguments == {"title": "Ship it"}
