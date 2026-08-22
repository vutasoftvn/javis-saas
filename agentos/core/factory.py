from __future__ import annotations

from pathlib import Path
from typing import Any

from agentos.core.adapters.model_gateway import build_model_provider
from agentos.core.approval import ApprovalService
from agentos.core.audit_sink import SqliteAuditSink
from agentos.core.model_provider import ModelProvider
from agentos.core.policy import PolicyEngine
from agentos.core.runtime import AgentRuntime
from agentos.core.trace_sink import SqliteTraceSink
from agentos.memory.retriever import MemoryRetriever
from agentos.memory.store import MemoryStore, get_memory_store
from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import SkillRouter
from agentos.tools.registry import ToolRegistry

_SKILLPACKS_ROOT = Path(__file__).resolve().parents[2] / "skillpacks"


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


def build_cosa_agent_plane(
    *,
    model_provider: ModelProvider | None = None,
    tool_registry: ToolRegistry | None = None,
    encore_client: Any | None = None,
    memory_store: MemoryStore | None = None,
    skill_registry: SkillRegistry | None = None,
    skillpacks_root: Path | None = None,
    policy_engine: PolicyEngine | None = None,
    approval_service: ApprovalService | None = None,
    trace_sink: SqliteTraceSink | None = None,
    audit_sink: SqliteAuditSink | None = None,
) -> AgentRuntime:
    """Production composition root (addendum §7 / COSA_ARCHITECTURE_REVIEW_2026-08-22.md).

    Unlike `build_default_runtime()`, this wires everything the acceptance
    criteria in the addendum require in a single `AgentRuntime`: registered
    Business Service Cluster tools, memory retrieval, skill routing, and a
    shared governance audit trail across `PolicyEngine`/`ApprovalService` —
    so these dependencies exist in the running composition, not only in
    source. Every parameter is overridable for tests/alternate deployments.
    """
    registry = tool_registry or ToolRegistry()
    registry.register_cluster_tools(encore_client)

    memory_retriever = MemoryRetriever(memory_store or get_memory_store())

    skills = skill_registry or SkillRegistry()
    if not skills.list():
        skills.discover(skillpacks_root or _SKILLPACKS_ROOT)
    skill_router = SkillRouter(skills)
    skill_instruction_loader = SkillInstructionLoader(skills)

    audit = audit_sink or SqliteAuditSink()

    return AgentRuntime(
        model_provider=model_provider or build_model_provider(),
        tool_registry=registry,
        policy_engine=policy_engine or PolicyEngine(audit_sink=audit),
        approval_service=approval_service or ApprovalService(audit_sink=audit),
        trace_sink=trace_sink or SqliteTraceSink(),
        memory_retriever=memory_retriever,
        skill_router=skill_router,
        skill_instruction_loader=skill_instruction_loader,
    )
