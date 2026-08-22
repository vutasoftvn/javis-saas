from __future__ import annotations

from agentos.core.adapters.deepseek_harness_provider import DeepSeekHarnessModelProvider
from agentos.core.model_provider import ModelProvider
from agentos.core.runtime import AgentRuntime
from agentos.tools.registry import ToolRegistry


def build_default_runtime(
    *,
    model_provider: ModelProvider | None = None,
    tool_registry: ToolRegistry | None = None,
) -> AgentRuntime:
    """Construct an `AgentRuntime` wired to the real DeepSeek Harness model
    provider by default. Tests keep using `StubModelProvider` directly —
    this factory is for real (non-test) entrypoints only.
    """
    return AgentRuntime(
        model_provider=model_provider or DeepSeekHarnessModelProvider(),
        tool_registry=tool_registry or ToolRegistry(),
    )
