# backend/app/workforce/agents/orchestration/adk/session_bridge.py
"""Projector mỏng: chuyển lifecycle event quan trọng của ADK Workflow sang
AgentEventRecord/mission_control_bus hiện có. KHÔNG phải 1 audit trail thứ 4 —
DatabaseSessionService (Task 9) là nơi ADK tự lưu session/event/replay-state đầy
đủ trong schema `adk_runtime` riêng; hàm này chỉ chiếu 1 phần nhỏ (tên node, tóm
tắt output) sang audit ledger canonical mà UI/founder đang đọc.
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from google.adk.events.event import Event

from agent_runtime.events.models import AgentEventRecord
from core.snowflake import generate_snowflake_id
from workforce.agents.orchestration.mission_control_bus import mission_control_bus


def _summarize_content(event: Event) -> str | None:
    if event.content is None or not event.content.parts:
        return None
    texts = [p.text for p in event.content.parts if p.text]
    return "\n".join(texts) if texts else None


def project_adk_event(
    db: Session,
    event: Event,
    *,
    mission_run_id: int,
    workspace_id: int,
    agent_key: str = "chief_of_staff",
) -> AgentEventRecord:
    next_sequence = int(
        db.query(func.max(AgentEventRecord.sequence))
        .filter(AgentEventRecord.run_id == mission_run_id)
        .scalar()
        or 0
    ) + 1

    payload: dict[str, Any] = {
        "author": event.author,
        "output": event.output,
        "text": _summarize_content(event),
    }

    raw_ts = getattr(event, "timestamp", None)
    if isinstance(raw_ts, (int, float)):
        event_time = datetime.fromtimestamp(raw_ts, timezone.utc)
    elif isinstance(raw_ts, datetime):
        event_time = raw_ts
    else:
        event_time = datetime.now(timezone.utc)

    record = AgentEventRecord(
        id=generate_snowflake_id(),
        run_id=mission_run_id,
        company_id=None,
        sequence=next_sequence,
        agent_key=agent_key,
        actor_type="adk_node",
        actor_id=event.author or "unknown",
        status="completed",
        event_type="adk.node_completed",
        event_time=event_time,
        payload_jsonb=payload,
    )

    db.add(record)

    mission_control_bus.emit_event(
        run_id=str(mission_run_id),
        workspace_id=str(workspace_id),
        event_type="adk.node_completed",
        data=payload,
        agent_key=agent_key,
    )
    return record
