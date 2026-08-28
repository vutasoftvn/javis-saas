"""Task 1: inbox.record() ghi aggregate_type/aggregate_id để RunCounter
rate-limit theo aggregate/ngày."""
import pytest

from apps.cosa.events import inbox

pytestmark = pytest.mark.asyncio


class _RecordingConn:
    def __init__(self):
        self.calls = []

    async def fetchrow(self, query, *args):
        self.calls.append((query, args))
        return {"id": 1}

    async def execute(self, query, *args):
        self.calls.append((query, args))


async def test_record_includes_aggregate_columns():
    conn = _RecordingConn()
    await inbox.record(
        conn,
        workspace_id="ws_1",
        event_id="e_1",
        consumer_name="agentos.event_intake",
        event_type="operations.task.created.v1",
        correlation_id="c_1",
        outcome="pending",
        aggregate_type="task",
        aggregate_id="t_1",
    )
    query, args = conn.calls[0]
    assert "aggregate_type" in query and "aggregate_id" in query
    assert "task" in args and "t_1" in args
