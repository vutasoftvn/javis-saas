from __future__ import annotations

import asyncio
import os

from agentos.core.adapters._tool_call_parsing import parse_tool_call
from agentos.core.model_provider import ModelResponse

_SDK_MODULE_NAME = "deepseek_harness"


class DeepSeekHarnessUnavailableError(RuntimeError):
    """Raised when the deepseek-harness-sdk is not installed or not configured."""


class DeepSeekHarnessModelProvider:
    """`ModelProvider` (agentos/core/model_provider.py) backed by the real
    `deepseek-harness-sdk` (PyPI, Developer Preview).

    Thin port of the model-call surface of the legacy
    `cosa_core.runtime.adapters.deepseek_harness.DeepSeekHarnessAdapter`
    (legacy/agent_runtime/cosa_core/runtime/adapters/deepseek_harness.py) —
    only the SDK invocation is ported. The legacy adapter's own tool-calling
    loop, budget/stuck-loop governance, and DB-backed AgentRun bookkeeping are
    intentionally NOT ported: agentos already has its own tool loop
    (agentos/core/executor.py) and governance (agentos/core/policy.py,
    agentos/core/approval.py), and CLAUDE.md §6 forbids forking DeepSeek
    Harness internals into Business Core — this keeps the adapter a
    single-purpose model-call primitive.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str = "deepseek-v4-flash",
        max_tokens: int | None = 4096,
    ) -> None:
        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self._base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self._model_name = model_name
        self._max_tokens = max_tokens

    def _import_sdk(self):
        try:
            from deepseek_harness import DeepSeekHarness, DeepSeekHarnessConfig
        except ImportError as exc:
            raise DeepSeekHarnessUnavailableError(
                f"deepseek-harness-sdk chưa được cài đặt: {exc}"
            ) from exc
        return DeepSeekHarness, DeepSeekHarnessConfig

    def _create_harness(self):
        if not self._api_key:
            raise DeepSeekHarnessUnavailableError("DEEPSEEK_API_KEY is not configured")
        DeepSeekHarness, DeepSeekHarnessConfig = self._import_sdk()
        config = DeepSeekHarnessConfig(
            api_key=self._api_key,
            base_url=self._base_url,
            model=self._model_name,
            max_tokens=self._max_tokens,
        )
        return DeepSeekHarness(config)

    @staticmethod
    def _build_prompt(system_prompt: str, messages: list[dict]) -> str:
        lines = [system_prompt, ""]
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", message)
            lines.append(f"[{role}] {content}")
        return "\n".join(lines)

    @staticmethod
    def _run_sync(harness, task: str):
        harness.start()
        try:
            return harness.run(task)
        finally:
            harness.close()

    async def generate(self, *, system_prompt: str, messages: list[dict]) -> ModelResponse:
        harness = self._create_harness()
        prompt = self._build_prompt(system_prompt, messages)
        result = await asyncio.to_thread(self._run_sync, harness, prompt)

        text = result.final_response or ""
        # Chưa điền `usage`/token-count ở đây — SDK không được cài trong môi
        # trường này để kiểm tra shape response thật, mà đoán tên field sẽ
        # âm thầm tạo ra số liệu cost giả (quy ước repo: chỉ dùng usage thật,
        # xem docstring TokenUsage). Sẽ nối khi xác nhận được field usage
        # thật của SDK.
        tool_call = parse_tool_call(text)
        if tool_call is not None:
            return ModelResponse(tool_call=tool_call, model=self._model_name)
        return ModelResponse(text=text, model=self._model_name)
