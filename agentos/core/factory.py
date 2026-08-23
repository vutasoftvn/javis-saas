from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from agentos.core.adapters.model_gateway import build_model_provider
from agentos.core.adapters.tenant_policy_client import TenantPolicyClient
from agentos.core.approval import ApprovalService
from agentos.core.audit_sink import SqliteAuditSink
from agentos.core.embedding_provider import EmbeddingProvider, StubEmbeddingProvider
from agentos.core.model_provider import ModelProvider
from agentos.core.policy import PolicyEngine
from agentos.core.runtime import AgentRuntime
from agentos.core.trace_sink import SqliteTraceSink
from agentos.knowledge.retrieval import KnowledgeRetriever
from agentos.knowledge.store import KnowledgeStore, get_knowledge_store
from agentos.memory.retriever import MemoryRetriever
from agentos.memory.store import MemoryStore, get_memory_store
from agentos.profiles.registry import ProfileRegistry
from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import SkillRouter
from agentos.tools.registry import ToolRegistry

_SKILLPACKS_ROOT = Path(__file__).resolve().parents[2] / "skillpacks"
_PROFILES_ROOT = Path(__file__).resolve().parents[1] / "profiles" / "definitions"


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
    memory_retriever: MemoryRetriever | None = None,
    knowledge_store: KnowledgeStore | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    knowledge_retriever: KnowledgeRetriever | None = None,
    skill_registry: SkillRegistry | None = None,
    skillpacks_root: Path | None = None,
    profile_registry: ProfileRegistry | None = None,
    profiles_root: Path | None = None,
    policy_engine: PolicyEngine | None = None,
    approval_service: ApprovalService | None = None,
    trace_sink: SqliteTraceSink | None = None,
    audit_sink: SqliteAuditSink | None = None,
    runtime_adapter: AgentRuntimeAdapter | None = None,
    tenant_policy_client: TenantPolicyClient | None = None,
) -> AgentRuntime:
    """Production composition root (addendum §7 / COSA_ARCHITECTURE_REVIEW_2026-08-22.md).

    Wires registered Business Service Cluster tools, memory retrieval, knowledge retrieval,
    skill routing, agent profile registry, and a shared governance audit trail across
    `PolicyEngine`/`ApprovalService` into a unified `AgentRuntime`.
    """
    registry = tool_registry or ToolRegistry()
    registry.register_cluster_tools(encore_client)

    mem_retriever = memory_retriever or MemoryRetriever(memory_store or get_memory_store())

    if knowledge_retriever is None:
        k_store = knowledge_store or get_knowledge_store()
        emb_provider = embedding_provider or StubEmbeddingProvider()
        know_retriever = KnowledgeRetriever(emb_provider, k_store)
    else:
        know_retriever = knowledge_retriever

    skills = skill_registry or SkillRegistry()
    if not skills.list():
        skills.discover(skillpacks_root or _SKILLPACKS_ROOT)
    skill_router = SkillRouter(skills)
    skill_instruction_loader = SkillInstructionLoader(skills)

    audit = audit_sink or SqliteAuditSink()

    profiles = profile_registry or ProfileRegistry()
    if not profiles.list():
        prof_root = profiles_root or _PROFILES_ROOT
        if prof_root.exists():
            profiles.discover(prof_root, skill_registry=skills, tool_registry=registry)

    runtime = AgentRuntime(
        model_provider=model_provider or build_model_provider(),
        tool_registry=registry,
        policy_engine=policy_engine or PolicyEngine(audit_sink=audit),
        approval_service=approval_service or ApprovalService(audit_sink=audit),
        trace_sink=trace_sink or SqliteTraceSink(),
        memory_retriever=mem_retriever,
        skill_router=skill_router,
        skill_instruction_loader=skill_instruction_loader,
        knowledge_retriever=know_retriever,
        runtime_adapter=runtime_adapter,
        tenant_policy_client=tenant_policy_client,
    )
    runtime._profile_registry = profiles
    return runtime
