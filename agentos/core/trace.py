from __future__ import annotations

import uuid
from typing import Any

from agentos.core.events import EventEnvelope, InMemoryEventBus


class TraceRecorder:
    """Per-run trace span list with optional parent/child linkage
    (blueprint §55: a run should have a trace tree, not just a flat log).
    Each span gets a unique span_id; passing parent_span_id to record()
    nests it under an earlier span.
    """

    def __init__(
        self,
        run_id: str,
        event_bus: InMemoryEventBus | None = None,
        correlation_id: str | None = None,
        workspace_id: str | None = None,
        company_id: str | None = None,
    ) -> None:
        self.run_id = run_id
        self._event_bus = event_bus or InMemoryEventBus()
        self.correlation_id = correlation_id
        self.workspace_id = workspace_id
        self.company_id = company_id
        self.spans: list[dict[str, Any]] = []

    def record(self, name: str, *, parent_span_id: str | None = None, **payload: Any) -> str:
        span_id = str(uuid.uuid4())
        corr_id = payload.get("correlation_id") or self.correlation_id
        ws_id = payload.get("workspace_id") or self.workspace_id
        comp_id = payload.get("company_id") or self.company_id

        span = {
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "name": name,
            "run_id": self.run_id,
            "correlation_id": corr_id,
            "workspace_id": ws_id,
            "company_id": comp_id,
            **payload,
        }
        self.spans.append(span)
        self._event_bus.publish(
            EventEnvelope(
                name=name,
                run_id=self.run_id,
                correlation_id=corr_id,
                workspace_id=ws_id,
                company_id=comp_id,
                payload=payload,
            )
        )
        return span_id

    def export(self) -> list[dict[str, Any]]:
        return list(self.spans)
