from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable, Optional

from pydantic import BaseModel, Field

from agentos.core.redaction import redact_payload


class ChatEvent(BaseModel):
    run_id: str
    conversation_id: str
    sequence: int
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None

    def to_sse_message(self) -> str:
        """Encodes event into SSE message format:
        id: <sequence>
        event: <event_type>
        data: <json_string>

        """
        # Ensure reasoning.status never exposes chain-of-thought
        safe_payload = dict(self.payload)
        if self.event_type == "reasoning.status":
            safe_payload = {
                "status": safe_payload.get("status", "thinking"),
                "tool": safe_payload.get("tool"),
                "step": safe_payload.get("step"),
            }
            # Remove any possible thought / reasoning chain fields
            safe_payload = {k: v for k, v in safe_payload.items() if v is not None}
        else:
            safe_payload = redact_payload(safe_payload)

        data = {
            "run_id": self.run_id,
            "conversation_id": self.conversation_id,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "payload": safe_payload,
            "correlation_id": self.correlation_id,
        }
        json_data = json.dumps(data, default=str)
        return f"id: {self.sequence}\nevent: {self.event_type}\ndata: {json_data}\n\n"


class RunEventStreamManager:
    """Manages active event streams, monotonic sequence allocation,
    and subscribers per run_id.
    """

    def __init__(self) -> None:
        self._run_events: dict[str, list[ChatEvent]] = {}
        self._sequences: dict[str, int] = {}
        self._subscribers: dict[str, list[asyncio.Queue[ChatEvent]]] = {}
        self._active_runs: set[str] = set()

    def start_run(self, run_id: str) -> None:
        self._run_events.setdefault(run_id, [])
        self._sequences[run_id] = 0
        self._active_runs.add(run_id)

    def is_active(self, run_id: str) -> bool:
        return run_id in self._active_runs

    def emit(
        self,
        *,
        run_id: str,
        conversation_id: str,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: Optional[str] = None,
        on_event_persisted: Optional[Callable[[ChatEvent], None]] = None,
    ) -> ChatEvent:
        if run_id not in self._sequences:
            self._sequences[run_id] = 0
            self._run_events.setdefault(run_id, [])

        self._sequences[run_id] += 1
        seq = self._sequences[run_id]

        event = ChatEvent(
            run_id=run_id,
            conversation_id=conversation_id,
            sequence=seq,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            payload=payload,
            correlation_id=correlation_id,
        )

        self._run_events[run_id].append(event)

        if on_event_persisted:
            on_event_persisted(event)

        if event_type in ("run.completed", "run.failed", "run.cancelled"):
            self._active_runs.discard(run_id)

        # Notify subscribers
        queues = self._subscribers.get(run_id, [])
        for q in list(queues):
            q.put_nowait(event)

        return event

    def get_events(self, run_id: str, since_sequence: Optional[int] = None) -> list[ChatEvent]:
        events = self._run_events.get(run_id, [])
        if since_sequence is not None:
            return [e for e in events if e.sequence > since_sequence]
        return list(events)

    async def stream_events(
        self,
        run_id: str,
        *,
        since_sequence: Optional[int] = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[str, None]:
        """Yields SSE lines for past events > since_sequence, then yields live events
        until the run completes or is terminal.
        """
        # First send past events
        past_events = self.get_events(run_id, since_sequence=since_sequence)
        last_sent_seq = since_sequence or 0
        for ev in past_events:
            if ev.sequence > last_sent_seq:
                last_sent_seq = ev.sequence
                yield ev.to_sse_message()

        # If run is already terminated, finish stream
        if not self.is_active(run_id) and past_events and past_events[-1].event_type in (
            "run.completed",
            "run.failed",
            "run.cancelled",
        ):
            return

        # Subscribe for live events
        queue: asyncio.Queue[ChatEvent] = asyncio.Queue()
        self._subscribers.setdefault(run_id, []).append(queue)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=timeout)
                    if event.sequence > last_sent_seq:
                        last_sent_seq = event.sequence
                        yield event.to_sse_message()

                    if event.event_type in ("run.completed", "run.failed", "run.cancelled"):
                        break
                except asyncio.TimeoutError:
                    # Keepalive comment
                    yield ": keepalive\n\n"
                    if not self.is_active(run_id):
                        break
        finally:
            if run_id in self._subscribers and queue in self._subscribers[run_id]:
                self._subscribers[run_id].remove(queue)


# Global singleton manager
_event_stream_manager = RunEventStreamManager()


def get_event_stream_manager() -> RunEventStreamManager:
    return _event_stream_manager


def reset_event_stream_manager_for_testing() -> RunEventStreamManager:
    global _event_stream_manager
    _event_stream_manager = RunEventStreamManager()
    return _event_stream_manager

