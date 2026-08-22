from __future__ import annotations

from typing import Protocol, runtime_checkable

from agentos.core.context import AgentContext


@runtime_checkable
class AgentRuntimeAdapter(Protocol):
    """Execution-runtime contract (addendum §6.5 / §19 Phase 3 "Runtime
    Convergence", ADR-B): the shape any execution runtime must satisfy to
    drive AgentRuntime's governed tool-calling loop for one run —
    `agentos.core.executor.Executor` (native — fallback/test per addendum
    §6.5) already satisfies it today. A future ADK-driven production
    adapter (addendum §6.2/§6.3) must satisfy the same contract so
    AgentRuntime does not need to know which one it got.

    Deliberately not extended into a new production adapter class yet:
    DeepSeek Harness is already the default `ModelProvider` for `Executor`
    in production (agentos/core/adapters/model_gateway.py's
    `build_model_provider()` defaults `CHAT_DEFAULT_PROVIDER=deepseek`),
    and `Executor`'s policy/approval gating never special-cases the model
    provider — see tests/agentos/test_runtime_convergence.py. A distinct
    "DeepSeek Harness runtime adapter" class would only earn its keep once
    an ADK orchestrator needs to drive a Harness session directly instead
    of going through this loop; adding one now would be an empty wrapper.
    """

    async def run(self, context: AgentContext) -> tuple[str, int]: ...
