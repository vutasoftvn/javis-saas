from __future__ import annotations

from typing import Any, Optional

from agent_core.contracts.errors import AgentRuntimeError, RuntimeErrorCode

__all__ = ["LiteLLMModelClient"]


class LiteLLMModelClient:
    """Model Gateway theo Blueprint V2 §7: bọc `litellm.acompletion()` dưới
    interface `.chat.completions.create(...)` tương thích OpenAI — dùng làm
    `model_client=` cho `OpenAIAgentsKernel` mà KHÔNG cần đổi kernel (litellm tự
    trả về response object cùng shape `choices[0].message.{content,tool_calls}`).

    litellm tự lo routing/retry/fallback/cost giữa provider (DeepSeek/OpenAI/
    Gemini/Claude/local) — không tự viết lại circuit breaker riêng ở đây, dùng
    cơ chế `fallbacks=` sẵn có của litellm thay vì trạng thái tuỳ chỉnh.
    """

    def __init__(
        self,
        *,
        model: str = "deepseek-chat",
        fallbacks: Optional[list[str]] = None,
        **default_kwargs: Any,
    ) -> None:
        self._model = model
        self._fallbacks = fallbacks or []
        self._default_kwargs = default_kwargs

    @property
    def chat(self) -> "_Chat":
        return _Chat(self)


class _Chat:
    def __init__(self, outer: LiteLLMModelClient) -> None:
        self.completions = _Completions(outer)


class _Completions:
    def __init__(self, outer: LiteLLMModelClient) -> None:
        self._outer = outer

    async def create(
        self,
        *,
        model: Optional[str] = None,
        messages: list[dict[str, Any]],
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> Any:
        import litellm

        call_kwargs = {**self._outer._default_kwargs, **kwargs}
        try:
            return await litellm.acompletion(
                model=model or self._outer._model,
                messages=messages,
                temperature=temperature,
                fallbacks=self._outer._fallbacks or None,
                **call_kwargs,
            )
        except litellm.exceptions.RateLimitError as exc:
            raise AgentRuntimeError(
                RuntimeErrorCode.MODEL_RATE_LIMIT, str(exc), retryable=True, cause=exc
            ) from exc
        except litellm.exceptions.ContextWindowExceededError as exc:
            raise AgentRuntimeError(
                RuntimeErrorCode.CONTEXT_LIMIT_EXCEEDED, str(exc), retryable=False, cause=exc
            ) from exc
        except litellm.exceptions.Timeout as exc:
            raise AgentRuntimeError(
                RuntimeErrorCode.MODEL_TIMEOUT, str(exc), retryable=True, cause=exc
            ) from exc
        except litellm.exceptions.AuthenticationError as exc:
            raise AgentRuntimeError(
                RuntimeErrorCode.TENANT_UNAUTHORIZED, str(exc), retryable=False, cause=exc
            ) from exc
        except Exception as exc:
            raise AgentRuntimeError(
                RuntimeErrorCode.MODEL_PROVIDER_ERROR, str(exc), retryable=True, cause=exc
            ) from exc
