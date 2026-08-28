from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional

from agent_core.runs.stream_events import RunStreamEventRecord, RunStreamEventRepository
from apps.cosa.api.schemas import EventEnvelopeDTO

import logging

__all__ = [
    "CosaEventStreamManager",
    "get_cosa_event_stream_manager",
    "UX_EVENT_TYPES",
    "redact_ux_event_payload",
]

logger = logging.getLogger(__name__)

TERMINAL_EVENT_TYPES = {"run.completed", "run.failed", "run.cancelled"}

UX_EVENT_TYPES = frozenset({
    "run.started",
    "reasoning.status",
    "message.started",
    "message.delta",
    "approval.required",
    "approval.resolved",
    "run.completed",
    "run.failed",
})

SENSITIVE_KEYS = frozenset({
    "secret_ref",
    "authorization_id",
    "access_token",
    "refresh_token",
    "delegation_token",
    "input_payload",
    "error_details",
    "raw_secret",
    "credentials",
    "token",
})


def redact_ux_event_payload(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive fields from UX event payloads.

    Only allowlisted safe fields are passed through. Unrecognized event types
    or sensitive credentials are stripped.
    """
    if event_type not in UX_EVENT_TYPES:
        logger.warning("Unrecognized UX event type '%s' requested for redaction", event_type)
        return {}

    redacted: dict[str, Any] = {}
    for k, v in payload.items():
        if k.lower() in SENSITIVE_KEYS:
            continue
        if isinstance(v, dict):
            # Shallow recursion for nested maps
            redacted[k] = {
                sub_k: sub_v for sub_k, sub_v in v.items()
                if sub_k.lower() not in SENSITIVE_KEYS
            }
        else:
            redacted[k] = v

    return redacted

# Không đóng stream chỉ vì im lặng 1 thời gian ngắn — dùng SSE keepalive
# comment (`: heartbeat`) theo interval hợp lý, đúng
# COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §7.3.
HEARTBEAT_INTERVAL_SEC = 15.0


class CosaEventStreamManager:
    """Canonical SSE Event Stream Manager cho COSA API.

    Durable từ 2026-08-25 (Phase 4/5, xem
    COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §7, §29.6): mọi
    event đi qua `emit()` được persist NGAY vào
    `agent_conversation.run_stream_events` (qua `RunStreamEventRepository`
    truyền vào mỗi lời gọi — không giữ state DB trong singleton này, tránh
    lazy module-global làm lifecycle chính §14.2) TRƯỚC khi fanout tới queue
    live. `_queues` giờ CHỈ còn là live-fanout optimization — nguồn sự thật
    cho replay là `repository.list_since()`, không phải RAM.

    KHÔNG dùng chung `agent_core.run_events` — xem comment chi tiết trong
    `packages/agent_core/migrations/011_run_stream_events.sql` (namespace
    event_type trùng nhưng payload shape khác với vocabulary nội bộ kernel,
    ghi chung sẽ tạo event trùng/xung đột khi replay).
    """

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[EventEnvelopeDTO]]] = {}

    def start_run(self, run_id: str) -> None:
        if run_id not in self._queues:
            self._queues[run_id] = []

    async def emit(
        self,
        repository: RunStreamEventRepository,
        *,
        run_id: str,
        conversation_id: str,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> EventEnvelopeDTO:
        if event_type in UX_EVENT_TYPES:
            safe_payload = redact_ux_event_payload(event_type, payload)
        else:
            safe_payload = {
                "event_ref": str(uuid.uuid4()),
                "hash": hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest(),
                "classification": "internal",
            }

        record = RunStreamEventRecord(
            run_id=run_id,
            event_type=event_type,
            payload=safe_payload,
            conversation_id=conversation_id,
            correlation_id=correlation_id,
        )
        persisted = await repository.append(record)

        envelope = EventEnvelopeDTO(
            run_id=persisted.run_id,
            conversation_id=persisted.conversation_id,
            sequence=persisted.sequence or 0,
            event_type=persisted.event_type,
            payload=persisted.payload,
            correlation_id=persisted.correlation_id,
            timestamp=persisted.created_at,
        )

        for q in self._queues.get(run_id, []):
            q.put_nowait(envelope)

        return envelope

    async def stream_events(
        self,
        repository: RunStreamEventRepository,
        run_id: str,
        since_sequence: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        q: asyncio.Queue[EventEnvelopeDTO] = asyncio.Queue()
        self._queues.setdefault(run_id, []).append(q)

        try:
            # 1. Replay từ durable store — sống sót qua API process restart,
            # không phụ thuộc client có kết nối liên tục hay không.
            past_events = await repository.list_since(run_id, after_sequence=since_sequence)
            has_terminal = False
            for ev in past_events:
                yield _format_sse(ev)
                if ev.event_type in TERMINAL_EVENT_TYPES:
                    has_terminal = True

            if has_terminal:
                return

            # 2. Live stream với heartbeat — không đóng stream khi im lặng
            # ngắn hạn, chỉ đóng khi gặp terminal event hoặc client disconnect
            # (client disconnect tự ngắt generator qua GeneratorExit của FastAPI
            # StreamingResponse).
            while True:
                try:
                    envelope = await asyncio.wait_for(q.get(), timeout=HEARTBEAT_INTERVAL_SEC)
                    yield _format_sse_envelope(envelope)
                    if envelope.event_type in TERMINAL_EVENT_TYPES:
                        break
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            queue_list = self._queues.get(run_id)
            if queue_list and q in queue_list:
                queue_list.remove(q)


def _format_sse(ev: RunStreamEventRecord) -> str:
    data_json = json.dumps(
        {
            "event_type": ev.event_type,
            "sequence": ev.sequence,
            "run_id": ev.run_id,
            "conversation_id": ev.conversation_id,
            "payload": ev.payload,
            "timestamp": ev.created_at.isoformat(),
            "correlation_id": ev.correlation_id,
        }
    )
    return f"id: {ev.sequence}\nevent: {ev.event_type}\ndata: {data_json}\n\n"


def _format_sse_envelope(ev: EventEnvelopeDTO) -> str:
    data_json = json.dumps(
        {
            "event_type": ev.event_type,
            "sequence": ev.sequence,
            "run_id": ev.run_id,
            "conversation_id": ev.conversation_id,
            "payload": ev.payload,
            "timestamp": ev.timestamp.isoformat(),
            "correlation_id": ev.correlation_id,
        }
    )
    return f"id: {ev.sequence}\nevent: {ev.event_type}\ndata: {data_json}\n\n"


_global_stream_manager = CosaEventStreamManager()


def get_cosa_event_stream_manager() -> CosaEventStreamManager:
    return _global_stream_manager
