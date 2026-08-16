import asyncio
from collections import OrderedDict
from datetime import datetime, timezone
import json
import logging
from typing import Any, AsyncIterator, Optional

from app.core.events import publish_event, cross_process_event_listener, EventEnvelope
from app.core.snowflake import generate_snowflake_str

logger = logging.getLogger(__name__)

# Standard Event Types (§P0.4, C1/C2 spec)
MISSION_STARTED = "mission_started"
MISSION_WAITING_APPROVAL = "mission_waiting_approval"
SUBAGENT_DELEGATED = "subagent_delegated"
SUBAGENT_COMPLETED = "subagent_completed"
TOOL_REQUESTED = "tool_requested"
TOOL_COMPLETED = "tool_completed"
VERIFICATION_PASSED = "verification_passed"
VERIFICATION_FAILED = "verification_failed"
MISSION_COMPLETED = "mission_completed"
MISSION_FAILED = "mission_failed"
MISSION_CANCELLED = "mission_cancelled"


class MissionControlBus:
    """Event bus broadcasting live multi-agent execution events to SSE subscribers and cross-process broker."""

    # Bounded history of event_ids emitted directly on this process, used to dedupe the
    # NOTIFY loop-back of our own events (see _on_cross_process_envelope).
    _RECENT_EVENT_IDS_MAXLEN = 500

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        self._recently_emitted_ids: "OrderedDict[str, None]" = OrderedDict()
        # Bridge cross-process NOTIFY deliveries (received via app.core.events'
        # CrossProcessEventListener, on WHATEVER process receives them) back into this
        # process's local subscriber queues. Without this, mission_control_bus.subscribe()
        # only ever sees events emitted by emit_event() on the SAME process, so a Founder Hub
        # SSE client connected to process B never sees a mission emitted on process A.
        cross_process_event_listener.add_raw_subscriber(self._on_cross_process_envelope)

    def _remember_emitted(self, event_id: str) -> None:
        self._recently_emitted_ids[event_id] = None
        if len(self._recently_emitted_ids) > self._RECENT_EVENT_IDS_MAXLEN:
            self._recently_emitted_ids.popitem(last=False)

    def emit_event(
        self,
        run_id: str,
        workspace_id: str,
        event_type: str,
        data: Optional[dict[str, Any]] = None,
        agent_key: Optional[str] = None,
    ) -> dict[str, Any]:
        event_id = generate_snowflake_str()
        event = {
            "event_id": event_id,
            "run_id": run_id,
            "workspace_id": workspace_id,
            "agent_key": agent_key or "chief_of_staff",
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        }
        # Recorded before dispatch so that when this same event loops back through NOTIFY
        # (Postgres delivers NOTIFY to every session listening on the channel in this database,
        # including one running in the very process that sent it), _on_cross_process_envelope
        # can recognize it as already delivered locally and skip re-pushing it.
        self._remember_emitted(event_id)

        # 1. Cross-process fan-out via Postgres LISTEN/NOTIFY broker
        try:
            ws_int = int(workspace_id)
            publish_event(
                event_type=f"mission.{event_type}",
                workspace_id=ws_int,
                payload=event,
                correlation_id=run_id,
            )
        except Exception as exc:
            logger.debug(f"[MissionControlBus] publish_event non-critical notice: {exc}")

        # 2. Dispatch to local queues for direct SSE subscribers in current process
        queues = self._subscribers.get(run_id, set())
        for q in list(queues):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

        logger.debug(f"[MissionControlBus] Emitted {event_type} for run {run_id}")
        return event

    def _on_cross_process_envelope(self, envelope: EventEnvelope) -> None:
        """Registered with CrossProcessEventListener (app.core.events) as a raw subscriber.

        Called synchronously whenever ANY process's NOTIFY for the shared platform_events
        channel is received on THIS process - regardless of which process originally called
        emit_event(). This is what makes mission_control_bus.subscribe() see mission events
        emitted on a different process (e.g. a worker_main.py background job calling
        chief_of_staff.py), not only ones emitted locally.
        """
        if not envelope.event_type.startswith("mission."):
            return
        event = envelope.payload or {}
        event_id = event.get("event_id")
        if event_id and event_id in self._recently_emitted_ids:
            # Already delivered directly by emit_event() step 2 on this same process - this
            # is just that same event looping back through NOTIFY.
            return
        run_id = envelope.correlation_id or event.get("run_id")
        if not run_id:
            return
        queues = self._subscribers.get(run_id, set())
        for q in list(queues):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

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
