"""Fact dự án do FOUNDER xác nhận — không ghi suy diễn của LLM (G-8).

Lưu trong `agent_memory.agent_memories` (MemoryService generic) với
`scope_type=PROJECT`, `scope_id=<project_id>`, `kind=SEMANTIC`,
`agent_key=founder`, provenance người xác nhận + message nguồn. Memory không
phải business truth: mâu thuẫn với Company Service thì Company thắng.
Agent chỉ ĐỀ XUẤT (capability `memory.fact.propose` chèn thẻ `memory_confirm`);
chỉ route có danh tính founder mới ghi.
"""

from __future__ import annotations

from typing import Any

from agent.memory.models import MemoryItem, MemoryKind

__all__ = [
    "MAX_FACT_CHARS",
    "PROJECT_SCOPE",
    "fact_view",
    "list_project_facts",
    "record_project_fact",
    "retract_project_fact",
]

PROJECT_SCOPE = "PROJECT"
MAX_FACT_CHARS = 500
_FACT_AGENT_KEY = "founder"
_RECALL_LIMIT = 20


def fact_view(item: MemoryItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "content": item.content,
        "confirmed_by": item.provenance.get("confirmed_by"),
        "source_message_id": item.provenance.get("source_message_id"),
        "created_at": item.created_at.isoformat(),
    }


async def record_project_fact(
    memory_service: Any,
    *,
    workspace_id: str,
    project_id: str,
    content: str,
    confirmed_by: str,
    source_message_id: str | None = None,
) -> MemoryItem:
    text = " ".join((content or "").split())
    if not text:
        raise ValueError("fact content is required")
    if len(text) > MAX_FACT_CHARS:
        raise ValueError(f"fact content must be <= {MAX_FACT_CHARS} characters")
    return await memory_service.record_memory(
        workspace_id=workspace_id,
        agent_key=_FACT_AGENT_KEY,
        kind=MemoryKind.SEMANTIC,
        content=text,
        importance=0.8,
        tags=("founder_confirmed",),
        scope_type=PROJECT_SCOPE,
        scope_id=project_id,
        provenance={
            "confirmed_by": confirmed_by,
            **({"source_message_id": source_message_id} if source_message_id else {}),
        },
    )


async def list_project_facts(
    memory_service: Any, *, workspace_id: str, project_id: str, limit: int = _RECALL_LIMIT
) -> list[MemoryItem]:
    return await memory_service.retrieve_memories(
        workspace_id=workspace_id,
        agent_key=_FACT_AGENT_KEY,
        kind=MemoryKind.SEMANTIC,
        limit=limit,
        scope_type=PROJECT_SCOPE,
        scope_id=project_id,
    )


async def retract_project_fact(
    memory_service: Any, *, workspace_id: str, project_id: str, fact_id: str, reason: str | None
) -> MemoryItem | None:
    return await memory_service.retract_memory(
        workspace_id=workspace_id,
        memory_id=fact_id,
        scope_type=PROJECT_SCOPE,
        scope_id=project_id,
        reason=reason,
    )
