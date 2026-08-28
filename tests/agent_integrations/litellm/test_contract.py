"""Contract and smoke tests for LiteLLM adapter (LiteLLMModelClient).

Asserts:
- Adapter initializes with default config and custom options.
- .chat.completions.create calls litellm.acompletion with correct kwargs.
- Provider errors are accurately mapped to typed AgentRuntimeError codes:
  - RateLimitError -> MODEL_RATE_LIMIT (retryable=True)
  - ContextWindowExceededError -> CONTEXT_LIMIT_EXCEEDED (retryable=False)
  - Timeout -> MODEL_TIMEOUT (retryable=True)
  - AuthenticationError -> TENANT_UNAUTHORIZED (retryable=False)
  - General error -> MODEL_PROVIDER_ERROR (retryable=True)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import litellm.exceptions
import pytest
from agent_core.contracts.errors import AgentRuntimeError, RuntimeErrorCode
from agent_integrations.litellm.gateway import LiteLLMModelClient


def test_litellm_client_initialization():
    """Client initializes with default or custom parameters."""
    client = LiteLLMModelClient()
    assert client._model == "deepseek-chat"
    assert client._fallbacks == []
    assert client.chat is not None
    assert client.chat.completions is not None

    custom_client = LiteLLMModelClient(
        model="openai/gpt-4o-mini", fallbacks=["deepseek/deepseek-chat"], max_tokens=100
    )
    assert custom_client._model == "openai/gpt-4o-mini"
    assert custom_client._fallbacks == ["deepseek/deepseek-chat"]
    assert custom_client._default_kwargs == {"max_tokens": 100}


@pytest.mark.asyncio
async def test_litellm_client_create_success_call():
    """Client calls litellm.acompletion with mapped parameters."""
    client = LiteLLMModelClient(model="deepseek/deepseek-chat")
    mock_resp = {
        "id": "cmpl_123",
        "choices": [{"message": {"role": "assistant", "content": "hello"}}],
    }

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_resp

        res = await client.chat.completions.create(
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.7,
        )

        assert res == mock_resp
        mock_acompletion.assert_called_once_with(
            model="deepseek/deepseek-chat",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.7,
            fallbacks=None,
        )


@pytest.mark.asyncio
async def test_litellm_client_maps_rate_limit_error():
    """litellm.exceptions.RateLimitError -> RuntimeErrorCode.MODEL_RATE_LIMIT."""
    client = LiteLLMModelClient(model="deepseek/deepseek-chat")

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = litellm.exceptions.RateLimitError(
            message="Rate limit reached", model="deepseek-chat", llm_provider="deepseek"
        )

        with pytest.raises(AgentRuntimeError) as exc_info:
            await client.chat.completions.create(messages=[{"role": "user", "content": "hi"}])

        assert exc_info.value.code == RuntimeErrorCode.MODEL_RATE_LIMIT
        assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_litellm_client_maps_context_window_error():
    """litellm.exceptions.ContextWindowExceededError -> RuntimeErrorCode.CONTEXT_LIMIT_EXCEEDED."""
    client = LiteLLMModelClient(model="deepseek/deepseek-chat")

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = litellm.exceptions.ContextWindowExceededError(
            message="Too many tokens", model="deepseek-chat", llm_provider="deepseek"
        )

        with pytest.raises(AgentRuntimeError) as exc_info:
            await client.chat.completions.create(messages=[{"role": "user", "content": "hi"}])

        assert exc_info.value.code == RuntimeErrorCode.CONTEXT_LIMIT_EXCEEDED
        assert exc_info.value.retryable is False


@pytest.mark.asyncio
async def test_litellm_client_maps_timeout_error():
    """litellm.exceptions.Timeout -> RuntimeErrorCode.MODEL_TIMEOUT."""
    client = LiteLLMModelClient(model="deepseek/deepseek-chat")

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = litellm.exceptions.Timeout(
            message="Connection timed out", model="deepseek-chat", llm_provider="deepseek"
        )

        with pytest.raises(AgentRuntimeError) as exc_info:
            await client.chat.completions.create(messages=[{"role": "user", "content": "hi"}])

        assert exc_info.value.code == RuntimeErrorCode.MODEL_TIMEOUT
        assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_litellm_client_maps_auth_error():
    """litellm.exceptions.AuthenticationError -> RuntimeErrorCode.TENANT_UNAUTHORIZED."""
    client = LiteLLMModelClient(model="deepseek/deepseek-chat")

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = litellm.exceptions.AuthenticationError(
            message="Invalid API Key", model="deepseek-chat", llm_provider="deepseek"
        )

        with pytest.raises(AgentRuntimeError) as exc_info:
            await client.chat.completions.create(messages=[{"role": "user", "content": "hi"}])

        assert exc_info.value.code == RuntimeErrorCode.TENANT_UNAUTHORIZED
        assert exc_info.value.retryable is False


@pytest.mark.asyncio
async def test_litellm_client_maps_generic_error():
    """Generic Exception -> RuntimeErrorCode.MODEL_PROVIDER_ERROR."""
    client = LiteLLMModelClient(model="deepseek/deepseek-chat")

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = RuntimeError("Unknown upstream crash")

        with pytest.raises(AgentRuntimeError) as exc_info:
            await client.chat.completions.create(messages=[{"role": "user", "content": "hi"}])

        assert exc_info.value.code == RuntimeErrorCode.MODEL_PROVIDER_ERROR
        assert exc_info.value.retryable is True
