import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, AsyncIterator, Optional

from app.core.snowflake import generate_snowflake_str

logger = logging.getLogger(__name__)


class MissionControlBus:
    """Event bus broadcasting live multi-agent execution events to SSE subscribers."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = {}

    def emit_event(
        self,
        run_id: str,
        workspace_id: str,
        event_type: str,
        data: Optional[dict[str, Any]] = None,
        agent_key: Optional[str] = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": generate_snowflake_str(),
            "run_id": run_id,
            "workspace_id": workspace_id,
            "agent_key": agent_key or "chief_of_staff",
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        }

        # Dispatch to local queues
        queues = self._subscribers.get(run_id, set())
        for q in list(queues):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

        logger.debug(f"[MissionControlBus] Emitted {event_type} for run {run_id}")
        return event

    async def subscribe(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.setdefault(run_id, set()).add(queue)

        try:
            while True:
                event = await queue.get()
                yield event
                if event.get("event_type") in ("mission_completed", "mission_failed", "mission_cancelled"):
                    break
        finally:
            if run_id in self._subscribers:
                self._subscribers[run_id].discard(queue)
                if not self._subscribers[run_id]:
                    self._subscribers.pop(run_id, None)


mission_control_bus = MissionControlBus()
