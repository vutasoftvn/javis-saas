from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable, Optional
from apps.cosa.api.schemas import EventEnvelopeDTO

__all__ = ["CosaEventStreamManager", "get_cosa_event_stream_manager"]


class CosaEventStreamManager:
    """Canonical SSE Event Stream Manager cho COSA API.
    
    Phát tán các events từ OpenAIAgentsKernel và CapabilityGateway
    tới Client Flutter qua SSE text/event-stream.
    """

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[EventEnvelopeDTO]]] = {}
        self._history: dict[str, list[EventEnvelopeDTO]] = {}
        self._lock = asyncio.Lock()

    def start_run(self, run_id: str) -> None:
        if run_id not in self._history:
            self._history[run_id] = []
        if run_id not in self._queues:
            self._queues[run_id] = []

    def emit(
        self,
        *,
        run_id: str,
        conversation_id: str,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: Optional[str] = None,
        on_event_persisted: Optional[Callable[[EventEnvelopeDTO], None]] = None,
    ) -> EventEnvelopeDTO:
        if run_id not in self._history:
            self._history[run_id] = []

        seq = len(self._history[run_id]) + 1
        event = EventEnvelopeDTO(
            run_id=run_id,
            conversation_id=conversation_id,
            sequence=seq,
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
            timestamp=datetime.now(timezone.utc),
        )

        self._history[run_id].append(event)

        if on_event_persisted:
            try:
                on_event_persisted(event)
            except Exception:
                pass

        for q in self._queues.get(run_id, []):
            q.put_nowait(event)

        return event

    async def stream_events(
        self, run_id: str, since_sequence: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        q: asyncio.Queue[EventEnvelopeDTO] = asyncio.Queue()

        if run_id not in self._queues:
            self._queues[run_id] = []
        self._queues[run_id].append(q)

        # 1. Replay historical events
        past_events = self._history.get(run_id, [])
        has_terminal = False
        for ev in past_events:
            if since_sequence is None or ev.sequence > since_sequence:
                data_json = json.dumps({
                    "event_type": ev.event_type,
                    "sequence": ev.sequence,
                    "run_id": ev.run_id,
                    "conversation_id": ev.conversation_id,
                    "payload": ev.payload,
                    "timestamp": ev.timestamp.isoformat(),
                    "correlation_id": ev.correlation_id,
                })
                yield f"id: {ev.sequence}\nevent: {ev.event_type}\ndata: {data_json}\n\n"
                if ev.event_type in ("run.completed", "run.failed", "run.cancelled"):
                    has_terminal = True

        if has_terminal:
            return

        # 2. Stream new live events
        try:
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=2.0)
                    data_json = json.dumps({
                        "event_type": ev.event_type,
                        "sequence": ev.sequence,
                        "run_id": ev.run_id,
                        "conversation_id": ev.conversation_id,
                        "payload": ev.payload,
                        "timestamp": ev.timestamp.isoformat(),
                        "correlation_id": ev.correlation_id,
                    })
                    yield f"id: {ev.sequence}\nevent: {ev.event_type}\ndata: {data_json}\n\n"

                    if ev.event_type in ("run.completed", "run.failed", "run.cancelled"):
                        break
                except asyncio.TimeoutError:
                    break

        finally:
            if run_id in self._queues and q in self._queues[run_id]:
                self._queues[run_id].remove(q)


_global_stream_manager = CosaEventStreamManager()


def get_cosa_event_stream_manager() -> CosaEventStreamManager:
    return _global_stream_manager
