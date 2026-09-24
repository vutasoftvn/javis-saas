"""Event runtime chưa phân loại (system.delivery) không có phase/status: DTO không được 500."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from apps.cosa.api.project_activity_routes import _event_record_to_dto


def test_dto_accepts_events_without_phase_and_status() -> None:
    now = datetime.now(UTC)
    record = SimpleNamespace(
        event_id="e1",
        workspace_id="ws",
        project_id="p",
        project_sequence=1,
        kind="system.delivery",
        phase=None,
        status=None,
        actor_kind="system",
        actor_id="worker",
        correlation_id=None,
        source_type="run",
        source_id="run_1",
        source_version="3",
        summary=None,
        classification="internal",
        payload_hash="h",
        occurred_at=now,
        recorded_at=now,
    )

    dto = _event_record_to_dto(record)

    assert dto.phase is None and dto.status is None
    assert dto.model_dump(mode="json")["kind"] == "system.delivery"
