from __future__ import annotations

from typing import Any

from agentos.core.events import EventEnvelope, InMemoryEventBus


class TraceRecorder:
    """Per-run trace span list. MVP scope: flat ordered list keyed to a
    single AgentRun; a full trace tree (blueprint §3.9) is a later phase.
    """

    def __init__(self, run_id: str, event_bus: InMemoryEventBus) -> None:
        self.run_id = run_id
        self._event_bus = event_bus
        self.spans: list[dict[str, Any]] = []

    def record(self, name: str, **payload: Any) -> None:
        span = {"name": name, "run_id": self.run_id, **payload}
        self.spans.append(span)
        self._event_bus.publish(EventEnvelope(name=name, run_id=self.run_id, payload=payload))

    def export(self) -> list[dict[str, Any]]:
        return list(self.spans)
