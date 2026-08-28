"""Phát `knowledge.source.published.v1` — CHỈ sau khi review đã approve,
trạng thái đã persist 'published', và KnowledgeSnapshot có identity xác thực
(P1 Task 6, spec DoD #6). Payload reference-only: không nội dung document/chunk.

Đường ghi thực tế (outbox) do composition root cung cấp qua `emit`. Business
event substrate hiện ở `services/company` (TS); Python-side sink là seam để
wire khi quyết định nơi review persist được chốt — mặc định chỉ log.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from agent_core.knowledge.snapshot import KnowledgeSnapshot

__all__ = ["publish_knowledge_source"]

logger = logging.getLogger("cosa.knowledge_ingestion.publish")

EmitFn = Callable[[dict], "Awaitable[None] | None"]


async def _default_emit(envelope: dict) -> None:
    from apps.cosa.knowledge_ingestion.event_sink import CompanyOutboxEventSink

    await CompanyOutboxEventSink()(envelope)


async def publish_knowledge_source(
    *,
    snapshot: KnowledgeSnapshot,
    approved: bool,
    persisted: bool,
    reviewed_by: str,
    reviewed_at: str,
    correlation_id: str,
    emit: EmitFn | None = None,
) -> None:
    if not (approved and persisted and snapshot.definition_hash):
        return

    envelope = {
        "eventId": str(uuid.uuid4()),
        "eventType": "knowledge.source.published.v1",
        "schemaVersion": 1,
        "occurredAt": datetime.now(UTC).isoformat(),
        "workspaceId": snapshot.workspace_id,
        "aggregateType": "knowledge_source",
        "aggregateId": snapshot.id,
        "correlationId": correlation_id,
        "actor": {"kind": "user", "id": reviewed_by},
        "producer": {"service": "cosa.knowledge_ingestion", "version": "1"},
        "classification": "internal",
        "payload": {
            "sourceId": snapshot.id,
            "snapshotId": snapshot.to_pinned_identity().definition_hash,
            "embeddingModel": snapshot.embedding_model,
            "indexRecipeVersion": snapshot.index_recipe_version,
            "reviewedBy": reviewed_by,
            "reviewedAt": reviewed_at,
        },
    }

    sink = emit or _default_emit
    result = sink(envelope)
    if result is not None:
        await result
