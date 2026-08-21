"""Agent Event Bus for broadcasting runtime state transitions and progress to Realtime / SSE.

Emits structured, sanitized events matching JaredRhod / Hologram Hub Visualizer specifications.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from workforce.agents.governance.models import AgentEventRecord
from core.events import publish_event
from core.snowflake import generate_snowflake_id

logger = logging.getLogger(__name__)


def publish_agent_event(
    db: Session,
    workspace_id: int,
    run_id: int,
    state: str,
    label: str,
    detail_safe: str,
    agent_key: str = "agent",
    progress: Optional[float] = None,
    risk: str = "low",
    requires_approval: bool = False,
    extra_metadata: Optional[dict[str, Any]] = None,
) -> AgentEventRecord:
    """Broadcast an agent runtime event over PostgreSQL LISTEN/NOTIFY and record in audit table."""
    now = datetime.now(timezone.utc)

    # 1. Prepare sanitized, user-safe payload (NO chain-of-thought, NO raw prompts)
    payload = {
        "run_id": str(run_id),
        "agent_key": agent_key,
        "state": state,  # e.g. "understanding", "routing", "priming", "tool_running", "waiting_approval", "completed", "error"
        "label": label,
        "detail_safe": detail_safe,
        "progress": progress,
        "risk": risk,
        "requires_approval": requires_approval,
        "timestamp": now.isoformat(),
    }
    if extra_metadata:
        payload["extra"] = extra_metadata

    # 2. Publish realtime event to PostgreSQL broker (streams to SSE & LiveKit clients)
    event_type = f"agent.{state}"
    try:
        publish_event(
            db=db,
            workspace_id=workspace_id,
            event_type=event_type,
            payload=payload,
        )
    except Exception as exc:
        logger.warning(f"[AgentEventBus] Failed to publish realtime event: {exc}")

    # 3. Persist audit record in AgentEventRecord
    record = AgentEventRecord(
        id=generate_snowflake_id(),
        run_id=run_id,
        agent_key=agent_key,
        event_type=event_type,
        status=state,
        payload_jsonb=payload,
        event_time=now,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return record
