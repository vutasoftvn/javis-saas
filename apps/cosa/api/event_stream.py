from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from agent.runs.stream_events import RunStreamEventRecord, RunStreamEventRepository

from apps.cosa.api.schemas import EventEnvelopeDTO

__all__ = [
    "UX_EVENT_TYPES",
    "CosaEventStreamManager",
    "get_cosa_event_stream_manager",
    "redact_ux_event_payload",
]

logger = logging.getLogger(__name__)

TERMINAL_EVENT_TYPES = {"run.completed", "run.failed", "run.cancelled"}

# Task 3 (plan 2026-09-11-project-scoped-founder-hub) — map SSE stream
# `event_type` sang Project Activity `kind` an toàn (SAFE_ACTIVITY_KINDS,
# apps/cosa/project_activity/service.py). Không có trong bảng này -> giữ
# nguyên event_type, ProjectActivityService tự fallback về "system.delivery"
# nếu nó cũng không nằm trong vocabulary an toàn của nó — event_stream.py
# không cần biết trước toàn bộ vocabulary, chỉ dịch những cái tên khác nhau
# giữa 2 tầng (vd. "approval.required" ở stream vs "approval.requested" ở
# Project Activity).
ACTIVITY_KIND_MAP: dict[str, str] = {
    "approval.required": "approval.requested",
    "approval.decided": "approval.resolved",
}

UX_EVENT_TYPES = frozenset(
    {
        "run.started",
        "reasoning.status",
        "message.started",
        "message.delta",
        "approval.required",
        "approval.resolved",
        "run.completed",
        "run.failed",
    }
)

SENSITIVE_KEYS = frozenset(
    {
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
    }
)


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
                sub_k: sub_v for sub_k, sub_v in v.items() if sub_k.lower() not in SENSITIVE_KEYS
            }
        else:
            redacted[k] = v

    return redacted


# Không đóng stream chỉ vì im lặng 1 thời gian ngắn — dùng SSE keepalive
# comment (`: heartbeat`) theo interval hợp lý, đúng
# COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §7.3.
HEARTBEAT_INTERVAL_SEC = 15.0

# Chu kỳ poll durable store để nhận event do tiến trình KHÁC (worker) ghi —
# xem `stream_events`.
POLL_INTERVAL_SEC = 1.0


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

    KHÔNG dùng chung `agent.run_events` — xem comment chi tiết trong
    `packages/agent/migrations/011_run_stream_events.sql` (namespace
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
        correlation_id: str | None = None,
        # Task 3 (plan 2026-09-11-project-scoped-founder-hub) — khi cả 3 đều
        # truyền vào, một Project Activity event idempotent cũng được ghi
        # TRƯỚC khi fanout live (đúng yêu cầu brief). Mặc định None — không
        # phá caller hiện có (test_event_stream.py gọi emit() không kèm 3
        # tham số này) và tự động bỏ qua projection cho run LEGACY_UNSCOPED
        # (project_id=None, trước Task 1/2).
        activity_service: Any | None = None,
        workspace_id: str | None = None,
        project_id: str | None = None,
    ) -> EventEnvelopeDTO:
        if event_type in UX_EVENT_TYPES:
            safe_payload = redact_ux_event_payload(event_type, payload)
        else:
            safe_payload = {
                "event_ref": str(uuid.uuid4()),
                "hash": hashlib.sha256(
                    json.dumps(payload, sort_keys=True).encode("utf-8")
                ).hexdigest(),
                "classification": "internal",
            }

        # Bug thật phát hiện qua E2E S10 (2026-09-14 schedule-project-scope):
        # `workspace_id`/`project_id` được nhận làm tham số (dùng cho Project
        # Activity projection ngay dưới) nhưng trước đây KHÔNG truyền vào
        # `RunStreamEventRecord` — mọi run_stream_event ghi ra, kể cả của run
        # project-scoped, đều có cột `project_id`/`workspace_id` NULL
        # (LEGACY_UNSCOPED) trong DB thật. `RunStreamEventRecord` đã khai báo
        # 2 field này từ 2026-09-11 (Project-scoped Founder Hub) chính để
        # phục vụ scoped fanout query — chỉ thiếu truyền vào lúc construct.
        record = RunStreamEventRecord(
            run_id=run_id,
            event_type=event_type,
            payload=safe_payload,
            conversation_id=conversation_id,
            correlation_id=correlation_id,
            workspace_id=workspace_id,
            project_id=project_id,
        )
        persisted = await repository.append(record)

        # Project Activity projection — ghi TRƯỚC live fanout (dưới), dùng
        # sequence vừa persist ở run_stream_events làm source_version để mỗi
        # stream event chỉ chiếu vào đúng 1 hàng Project Activity.
        if activity_service is not None and workspace_id and project_id:
            await activity_service.record_runtime_event(
                workspace_id=workspace_id,
                project_id=project_id,
                kind=ACTIVITY_KIND_MAP.get(event_type, event_type),
                source_type="run",
                source_id=run_id,
                source_version=str(persisted.sequence or 0),
                correlation_id=correlation_id,
                raw_context=payload,
                occurred_at=persisted.created_at,
            )

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

        # Pump Prometheus runtime metrics at event emit points
        try:
            from apps.cosa.observability.metrics import (
                record_approval,
                record_run_outcome,
                record_tool_call,
            )

            if event_type == "run.completed":
                record_run_outcome("completed")
            elif event_type == "run.failed":
                record_run_outcome("failed")
            elif event_type == "run.cancelled":
                record_run_outcome("cancelled")
            elif event_type == "approval.required":
                record_run_outcome("waiting_approval")
            elif event_type in ("approval.decided", "approval.resolved"):
                decision = safe_payload.get("status") or safe_payload.get("decision") or "approved"
                record_approval(decision)
            elif event_type == "tool.completed":
                cap = safe_payload.get("capability") or safe_payload.get("tool") or "capability"
                record_tool_call(cap, "success")
            elif event_type == "tool.failed":
                cap = safe_payload.get("capability") or safe_payload.get("tool") or "capability"
                record_tool_call(cap, "failed")
        except Exception:
            pass

        return envelope

    async def stream_events(
        self,
        repository: RunStreamEventRepository,
        run_id: str,
        since_sequence: int | None = None,
    ) -> AsyncGenerator[str, None]:
        q: asyncio.Queue[EventEnvelopeDTO] = asyncio.Queue()
        self._queues.setdefault(run_id, []).append(q)

        try:
            # 1. Replay từ durable store — sống sót qua API process restart,
            # không phụ thuộc client có kết nối liên tục hay không.
            last_sequence = since_sequence
            past_events = await repository.list_since(run_id, after_sequence=since_sequence)
            has_terminal = False
            for ev in past_events:
                yield _format_sse(ev)
                last_sequence = ev.sequence
                if ev.event_type in TERMINAL_EVENT_TYPES:
                    has_terminal = True

            if has_terminal:
                return

            # 2. Live stream với heartbeat — không đóng stream khi im lặng
            # ngắn hạn, chỉ đóng khi gặp terminal event hoặc client disconnect
            # (client disconnect tự ngắt generator qua GeneratorExit của FastAPI
            # StreamingResponse).
            #
            # Queue RAM chỉ nhận event `emit()` trong CÙNG process. Worker
            # (`apps.cosa.worker.main`) chạy tiến trình riêng: event của nó chỉ
            # đi vào durable store, nên phải poll `list_since()` định kỳ —
            # thiếu bước này SSE chỉ phát heartbeat mãi, chat hiện bong bóng
            # trả lời rỗng dù run đã xong. `last_sequence` chống phát trùng
            # khi cùng 1 event tới từ cả queue lẫn poll.
            loop = asyncio.get_running_loop()
            last_output_at = loop.time()
            while True:
                try:
                    envelope = await asyncio.wait_for(q.get(), timeout=POLL_INTERVAL_SEC)
                    if last_sequence is not None and envelope.sequence <= last_sequence:
                        continue
                    yield _format_sse_envelope(envelope)
                    last_sequence = envelope.sequence
                    last_output_at = loop.time()
                    if envelope.event_type in TERMINAL_EVENT_TYPES:
                        break
                    continue
                except TimeoutError:
                    pass

                terminal = False
                for ev in await repository.list_since(run_id, after_sequence=last_sequence):
                    yield _format_sse(ev)
                    last_sequence = ev.sequence
                    last_output_at = loop.time()
                    if ev.event_type in TERMINAL_EVENT_TYPES:
                        terminal = True
                        break
                if terminal:
                    break

                if loop.time() - last_output_at >= HEARTBEAT_INTERVAL_SEC:
                    yield ": heartbeat\n\n"
                    last_output_at = loop.time()
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
