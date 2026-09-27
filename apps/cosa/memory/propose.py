"""`memory.fact.propose` — agent ĐỀ XUẤT 1 fact để founder xác nhận (G-8).

Không ghi memory: chỉ chèn message có cấu trúc `{"kind": "memory_confirm",
"fact": ...}` vào conversation đang chat + Project Activity `agent.chat_message`
để UI hiện thẻ ngay. Founder bấm "Lưu" -> POST /agent/projects/:id/memory/facts.
"""

from __future__ import annotations

import json
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.conversations.models import MessageRecord
from agent.governance.contracts import CapabilityRisk

from apps.cosa.memory.project_facts import MAX_FACT_CHARS

__all__ = ["MEMORY_FACT_PROPOSE_SPEC", "create_memory_fact_propose_handler"]

MEMORY_FACT_PROPOSE_SPEC = CapabilitySpec(
    id="memory.fact.propose",
    description=(
        "Đề xuất lưu 1 sự thật quan trọng, ổn định về dự án (quyết định, ràng buộc, ưu "
        "tiên, số liệu founder vừa nói) vào trí nhớ dự án. Founder phải bấm xác nhận thì "
        "mới được lưu. Chỉ đề xuất điều founder đã nói/đồng ý, không đề xuất suy đoán."
    ),
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["fact"],
        "properties": {"fact": {"type": "string", "minLength": 5, "maxLength": MAX_FACT_CHARS}},
    },
    output_schema={"type": "object", "properties": {"proposed": {"type": "boolean"}}},
)


def create_memory_fact_propose_handler(plane: Any):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        from apps.cosa.worker.wga_run import record_agent_chat_message_activity

        ctx = context if isinstance(context, dict) else {}
        workspace_id = str(ctx.get("workspace_id") or "")
        project_id = str(ctx.get("project_id") or "")
        conversation_id = str(ctx.get("conversation_id") or "")
        if not (workspace_id and project_id and conversation_id):
            raise ValueError(
                "memory.fact.propose: workspace_id/project_id/conversation_id missing from context"
            )
        fact = " ".join(str(payload.get("fact") or "").split())
        if len(fact) < 5:
            raise ValueError("memory.fact.propose: fact is required")
        fact = fact[:MAX_FACT_CHARS]
        run_ref = str(ctx.get("correlation_id") or "")
        stored = await plane.conversation_repository.add_message(
            MessageRecord(
                conversation_id=conversation_id,
                project_id=project_id,
                role="assistant",
                content=json.dumps({"kind": "memory_confirm", "fact": fact}, ensure_ascii=False),
                run_id=run_ref or None,
                status="completed",
            )
        )
        await record_agent_chat_message_activity(
            plane,
            workspace_id=workspace_id,
            project_id=project_id,
            conversation_id=conversation_id,
            message=stored,
            run_id=run_ref or "memory_propose",
            message_kind="memory_confirm",
        )
        return {"proposed": True, "fact": fact}

    return handler
