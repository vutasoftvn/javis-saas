from __future__ import annotations

import asyncio
import time
from typing import Any
import pytest

from agentos.core.approval import ApprovalService, ApprovalStatus
from agentos.core.audit_sink import SqliteAuditSink
from agentos.core.context_builder import ContextBuilder
from agentos.core.embedding_provider import StubEmbeddingProvider
from agentos.core.model_provider import ModelResponse, ToolCallRequest
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.core.policy import ExecutionMode, PermissionLevel, PolicyEngine, ToolRiskLevel
from agentos.core.runtime import AgentRuntime
from agentos.core.trace_sink import SqliteTraceSink
from agentos.knowledge.models import KnowledgeChunk
from agentos.knowledge.retrieval import KnowledgeRetriever
from agentos.knowledge.store import InMemoryKnowledgeStore
from agentos.memory.store import InMemoryMemoryStore
from agentos.tools.clusters.strategy_tools import get_strategy_tools
from agentos.tools.encore_client import EncoreClient
from agentos.tools.registry import ToolRegistry


class _FastMockModel:
    async def generate(self, system_prompt: str, messages: list[dict[str, Any]]) -> ModelResponse:
        # Simulate standard 5ms inference latency
        await asyncio.sleep(0.005)
        return ModelResponse(text="Analysis complete. Ready for next step.")


@pytest.mark.asyncio
async def test_performance_baseline_and_100_concurrent_users():
    # Setup high-performance test infrastructure
    backend_store = InMemoryKnowledgeStore()
    embedding_provider = StubEmbeddingProvider()
    memory_store = InMemoryMemoryStore()
    retriever = KnowledgeRetriever(embedding_provider=embedding_provider, store=backend_store)

    tool_registry = ToolRegistry()
    for tool in get_strategy_tools(EncoreClient()):
        tool_registry.register(tool)

    audit_sink = SqliteAuditSink()
    policy_engine = PolicyEngine(audit_sink=audit_sink)
    approval_svc = ApprovalService(audit_sink=audit_sink)
    trace_sink = SqliteTraceSink()

    # Pre-populate knowledge chunks
    embeds = await embedding_provider.embed(["Enterprise SLA requires 99.99% uptime and < 500ms p99 latency."])
    await backend_store.put_chunks(
        [
            KnowledgeChunk(
                id="chunk_1",
                source_id="doc_ops_1",
                workspace_id="ws_perf",
                chunk_index=0,
                content="Enterprise SLA requires 99.99% uptime and < 500ms p99 latency.",
                embedding=embeds[0],
            )
        ]
    )

    context_builder = ContextBuilder(tool_registry, knowledge_retriever=retriever)

    # -------------------------------------------------------------------------
    # 1. Benchmark: Context Building Time
    # -------------------------------------------------------------------------
    ctx_times: list[float] = []
    for _ in range(20):
        t0 = time.perf_counter()
        task = TaskContext(
            goal="Evaluate enterprise SLA",
            agent_key="analyst",
            workspace_id="ws_perf",
        )
        ctx = await context_builder.build(task)
        ctx_times.append(time.perf_counter() - t0)
        assert len(ctx.tool_names) > 0

    avg_ctx_ms = (sum(ctx_times) / len(ctx_times)) * 1000
    assert avg_ctx_ms < 50.0, f"Context building too slow: {avg_ctx_ms:.2f}ms"

    # -------------------------------------------------------------------------
    # 2. Benchmark: Knowledge Retrieval Latency
    # -------------------------------------------------------------------------
    retrieval_times: list[float] = []
    for _ in range(20):
        t0 = time.perf_counter()
        results = await retriever.retrieve(workspace_id="ws_perf", query_text="uptime SLA", limit=3)
        retrieval_times.append(time.perf_counter() - t0)
        assert len(results) >= 1

    avg_retrieval_ms = (sum(retrieval_times) / len(retrieval_times)) * 1000
    assert avg_retrieval_ms < 20.0, f"Knowledge retrieval too slow: {avg_retrieval_ms:.2f}ms"

    # -------------------------------------------------------------------------
    # 3. Benchmark: Approval Pause & Resume Round-Trip
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    app = approval_svc.request_approval(action="deploy", subject="prod", requester="user_1")
    approval_svc.decide(app.id, reviewer="admin_1", approved=True)
    approval_roundtrip_ms = (time.perf_counter() - t0) * 1000
    assert approval_roundtrip_ms < 15.0, f"Approval roundtrip too slow: {approval_roundtrip_ms:.2f}ms"

    # -------------------------------------------------------------------------
    # 4. Load Test: 100 Concurrent Users Running Agent Loops
    # -------------------------------------------------------------------------
    runtime = AgentRuntime(
        model_provider=_FastMockModel(),
        tool_registry=tool_registry,
        policy_engine=policy_engine,
        approval_service=approval_svc,
        trace_sink=trace_sink,
    )

    async def single_user_session(user_idx: int) -> tuple[float, AgentRunStatus]:
        t_start = time.perf_counter()
        user_task = TaskContext(
            goal=f"User {user_idx} task inquiry",
            agent_key="co_founder",
            workspace_id=f"ws_user_{user_idx}",
            correlation_id=f"corr_load_{user_idx}",
            role="founder",
            agent_permission_level=PermissionLevel.L3_EXECUTE,
        )
        res = await runtime.run(user_task)
        return (time.perf_counter() - t_start), res.status

    start_load = time.perf_counter()
    tasks = [single_user_session(i) for i in range(100)]
    results = await asyncio.gather(*tasks)
    total_load_duration = time.perf_counter() - start_load

    latencies = [lat for lat, _ in results]
    statuses = [st for _, st in results]

    # Verify zero failure / zero crash
    assert all(st == AgentRunStatus.COMPLETED for st in statuses), "Some concurrent runs failed!"
    assert len(results) == 100

    # Calculate p50 and p99
    latencies.sort()
    p50_latency_ms = latencies[int(len(latencies) * 0.5)] * 1000
    p99_latency_ms = latencies[int(len(latencies) * 0.99)] * 1000

    assert p99_latency_ms < 1000.0, f"p99 latency exceeded 1s: {p99_latency_ms:.2f}ms"
    assert total_load_duration < 5.0, f"Total 100 concurrent requests took {total_load_duration:.2f}s"
