from __future__ import annotations

from agentos.core.adapters.model_gateway import build_model_provider
from agentos.core.approval import ApprovalService
from agentos.core.model_provider import ModelProvider
from agentos.core.policy import PolicyEngine
from agentos.core.runtime import AgentRuntime
from agentos.core.trace_sink import SqliteTraceSink
from agentos.tools.registry import ToolRegistry


def build_default_runtime(
    *,
    model_provider: ModelProvider | None = None,
    tool_registry: ToolRegistry | None = None,
    policy_engine: PolicyEngine | None = None,
    approval_service: ApprovalService | None = None,
    trace_sink: SqliteTraceSink | None = None,
) -> AgentRuntime:
    """Construct an `AgentRuntime` wired to a real model provider by default,
    chosen via `build_model_provider()` (respects `CHAT_DEFAULT_PROVIDER`,
    falls back to DeepSeek Harness). Tests keep using `StubModelProvider`
    directly — this factory is for real (non-test) entrypoints only.

    `policy_engine`/`approval_service` default to real (non-bypassable)
    instances rather than None, so a caller that forgets to pass them
    still gets the CLAUDE.md §11 permission gate — not silent allow-all.
    `trace_sink` defaults to a real SqliteTraceSink so runs are durable by
    default (CLAUDE.md §10/§12); pass trace_sink=None explicitly only for
    tests that want in-memory-only traces.
    """
    return AgentRuntime(
        model_provider=model_provider or build_model_provider(),
        tool_registry=tool_registry or ToolRegistry(),
        policy_engine=policy_engine or PolicyEngine(),
        approval_service=approval_service or ApprovalService(),
        trace_sink=trace_sink or SqliteTraceSink(),
    )
