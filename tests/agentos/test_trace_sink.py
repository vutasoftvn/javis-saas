import pytest

from agentos.core.events import EventEnvelope, InMemoryEventBus
from agentos.core.trace_sink import SqliteTraceSink


@pytest.mark.asyncio
async def test_sqlite_trace_sink_persists_events(tmp_path):
    db_path = tmp_path / "traces.sqlite3"
    sink = SqliteTraceSink(db_path=db_path)
    bus = InMemoryEventBus()
    sink.attach(bus)

    bus.publish(EventEnvelope(name="tool_call.started", run_id="run-1", payload={"tool_name": "echo"}))
    bus.publish(EventEnvelope(name="tool_call.completed", run_id="run-1", payload={"result": {"ok": True}}))

    events = sink.export_run("run-1")
    assert [e["name"] for e in events] == ["tool_call.started", "tool_call.completed"]
    assert events[0]["payload"]["tool_name"] == "echo"

    sink.close()

    # Re-opening the same file should see the persisted rows (durability
    # across process restarts, not just in the live connection).
    reopened = SqliteTraceSink(db_path=db_path)
    assert len(reopened.export_run("run-1")) == 2
    reopened.close()


@pytest.mark.asyncio
async def test_sqlite_trace_sink_scopes_export_by_run_id(tmp_path):
    sink = SqliteTraceSink(db_path=tmp_path / "traces.sqlite3")
    bus_a = InMemoryEventBus()
    bus_b = InMemoryEventBus()
    sink.attach(bus_a)
    sink.attach(bus_b)

    bus_a.publish(EventEnvelope(name="agent_run.started", run_id="run-a", payload={}))
    bus_b.publish(EventEnvelope(name="agent_run.started", run_id="run-b", payload={}))

    assert len(sink.export_run("run-a")) == 1
    assert len(sink.export_run("run-b")) == 1
    sink.close()
