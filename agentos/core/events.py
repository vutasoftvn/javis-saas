from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel, Field

# Canonical event names follow "entity.action" (blueprint spec §3.9 / Master Architecture §46).
EVENT_AGENT_RUN_CREATED = "agent_run.created"
EVENT_AGENT_RUN_STARTED = "agent_run.started"
EVENT_AGENT_RUN_COMPLETED = "agent_run.completed"
EVENT_AGENT_RUN_FAILED = "agent_run.failed"
EVENT_TOOL_CALL_STARTED = "tool_call.started"
EVENT_TOOL_CALL_COMPLETED = "tool_call.completed"
EVENT_TOOL_CALL_DENIED = "tool_call.denied"
EVENT_TOOL_CALL_WAITING_APPROVAL = "tool_call.waiting_approval"
EVENT_MODEL_GENERATION_COMPLETED = "model_generation.completed"


class EventEnvelope(BaseModel):
    name: str
    run_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    emitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InMemoryEventBus:
    """MVP event bus for a single process/run. A durable, cross-process bus
    is Phase 8 scope (blueprint §4) — do not treat this as production-durable.
    """

    def __init__(self) -> None:
        self._subscribers: list[Callable[[EventEnvelope], None]] = []
        self.published: list[EventEnvelope] = []

    def subscribe(self, handler: Callable[[EventEnvelope], None]) -> None:
        self._subscribers.append(handler)

    def publish(self, event: EventEnvelope) -> None:
        self.published.append(event)
        for handler in self._subscribers:
            handler(event)
