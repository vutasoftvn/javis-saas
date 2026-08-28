"""P1 Task 6: knowledge.source.published.v1 chỉ fire khi review đã approve,
trạng thái đã persist 'published', và snapshot có identity (definition_hash).
Payload reference-only."""
import pytest

from agent_core.knowledge.snapshot import KnowledgeSnapshot
from apps.cosa.knowledge_ingestion.publish import publish_knowledge_source

pytestmark = pytest.mark.asyncio


def _snapshot(ws="ws_1"):
    return KnowledgeSnapshot(
        id="src_1", workspace_id=ws,
        embedding_model="none", embedding_version="0",
    ).with_hash()


async def test_emits_only_after_durable_approved_review():
    seen = []
    await publish_knowledge_source(
        snapshot=_snapshot(), approved=True, persisted=True,
        reviewed_by="u_1", reviewed_at="2026-08-28T11:00:00Z", correlation_id="corr_1",
        emit=lambda e: seen.append(e),
    )
    assert len(seen) == 1
    ev = seen[0]
    assert ev["eventType"] == "knowledge.source.published.v1"
    assert set(ev["payload"].keys()) == {
        "sourceId", "snapshotId", "embeddingModel", "indexRecipeVersion", "reviewedBy", "reviewedAt"
    }
    assert ev["workspaceId"] == "ws_1"
    assert ev["classification"] == "internal"


async def test_suppressed_when_not_persisted():
    seen = []
    await publish_knowledge_source(
        snapshot=_snapshot(), approved=True, persisted=False,
        reviewed_by="u_1", reviewed_at="t", correlation_id="c", emit=lambda e: seen.append(e),
    )
    assert seen == []


async def test_suppressed_when_not_approved():
    seen = []
    await publish_knowledge_source(
        snapshot=_snapshot(), approved=False, persisted=True,
        reviewed_by="u_1", reviewed_at="t", correlation_id="c", emit=lambda e: seen.append(e),
    )
    assert seen == []
