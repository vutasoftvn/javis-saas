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
async def test_sqlite_trace_sink_redacts_sensitive_fields_before_persisting(tmp_path):
    """Addendum §15.2 P0: raw payload must never be persisted unredacted.
    tool_call.started/completed events carry raw tool arguments/results
    (agentos/core/executor.py:118-128), which may contain API keys/tokens/
    passwords if a tool takes credentials as an argument."""
    sink = SqliteTraceSink(db_path=tmp_path / "traces.sqlite3")
    bus = InMemoryEventBus()
    sink.attach(bus)

    bus.publish(
        EventEnvelope(
            name="tool_call.started",
            run_id="run-1",
            payload={"tool_name": "send_email", "arguments": {"api_key": "sk-live-secret", "to": "a@b.com"}},
        )
    )

    events = sink.export_run("run-1")
    assert events[0]["payload"]["arguments"]["api_key"] == "***REDACTED***"
    assert events[0]["payload"]["arguments"]["to"] == "a@b.com"
    assert events[0]["payload"]["tool_name"] == "send_email"

    sink.close()


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


@pytest.mark.asyncio
async def test_sqlite_trace_sink_persists_correlation_and_tenant_scope(tmp_path):
    sink = SqliteTraceSink(db_path=tmp_path / "traces.sqlite3")
    bus = InMemoryEventBus()
    sink.attach(bus)

    bus.publish(
        EventEnvelope(
            name="agent_run.started",
            run_id="run-100",
            correlation_id="corr-xyz",
            workspace_id="ws-abc",
            company_id="comp-123",
            payload={"task": "do something"},
        )
    )

    events = sink.export_run("run-100")
    assert len(events) == 1
    assert events[0]["correlation_id"] == "corr-xyz"
    assert events[0]["workspace_id"] == "ws-abc"
    assert events[0]["company_id"] == "comp-123"
    assert events[0]["truncated"] is False

    # Scoped export by workspace_id
    scoped_events = sink.export_run("run-100", workspace_id="ws-abc")
    assert len(scoped_events) == 1
    other_scope = sink.export_run("run-100", workspace_id="ws-other")
    assert len(other_scope) == 0

    sink.close()


@pytest.mark.asyncio
async def test_sqlite_trace_sink_truncates_large_payloads(tmp_path):
    # Set small max_payload_bytes for testing
    sink = SqliteTraceSink(db_path=tmp_path / "traces.sqlite3", max_payload_bytes=100)
    bus = InMemoryEventBus()
    sink.attach(bus)

    large_payload = {"key": "x" * 500}
    bus.publish(EventEnvelope(name="tool_call.completed", run_id="run-large", payload=large_payload))

    events = sink.export_run("run-large")
    assert len(events) == 1
    assert events[0]["truncated"] is True
    assert events[0]["payload"]["truncated"] is True
    assert "preview" in events[0]["payload"]
    assert events[0]["payload"]["original_size"] > 100

    sink.close()
