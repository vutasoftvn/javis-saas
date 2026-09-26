"""Project Activity SSE phải đẩy event MỚI sau replay (worker ghi ở tiến trình
khác) — trước đây sau replay chỉ còn heartbeat."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from apps.cosa.api import project_activity_routes as routes


def _record(seq: int, kind: str = "agent.chat_message"):
    now = datetime.now(UTC)
    return SimpleNamespace(
        event_id=f"ev{seq}",
        workspace_id="ws1",
        project_id="p1",
        project_sequence=seq,
        kind=kind,
        phase=None,
        status=None,
        actor_kind="agent",
        actor_id="r",
        correlation_id="r",
        source_type="message",
        source_id=f"m{seq}",
        source_version="1",
        summary={"conversation_id": "conv_9", "message_kind": "plan_progress"},
        classification="activity",
        payload_hash="h",
        integrity_hash=None,
        occurred_at=now,
        recorded_at=now,
    )


class _Repo:
    def __init__(self) -> None:
        self.calls: list[int | None] = []
        self.rows = [_record(1)]

    async def list_since(self, *, workspace_id, project_id, after_sequence, limit):
        self.calls.append(after_sequence)
        return [r for r in self.rows if r.project_sequence > (after_sequence or 0)]


@pytest.mark.asyncio
async def test_stream_emits_events_written_after_replay(monkeypatch):
    monkeypatch.setattr(routes, "PROJECT_ACTIVITY_POLL_INTERVAL_SEC", 0.01)
    repo = _Repo()
    plane = SimpleNamespace(project_activity_repository=repo)
    identity = SimpleNamespace(workspace_id="ws1")

    gen = routes._stream_project_activity(plane, identity, "p1", None)
    assert await gen.__anext__() == "id: 1\n"
    await gen.__anext__()  # data của event replay

    repo.rows.append(_record(2))  # worker ghi thêm sau khi client đã kết nối
    assert await gen.__anext__() == "id: 2\n"
    data = await gen.__anext__()
    assert '"source_id":"m2"' in data
    await gen.aclose()
    # poll tiếp từ sequence cuối, không phát lại event 1
    assert repo.calls[0] is None and 1 in repo.calls
