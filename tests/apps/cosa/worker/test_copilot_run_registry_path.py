import pytest

from apps.cosa.worker.copilot_run import run_customer_support_copilot


class _StubStreamRepo: ...


class _RecordingStreamMgr:
    def __init__(self):
        self.events = []

    async def emit(self, repo, *, run_id, conversation_id, event_type, payload, correlation_id):
        self.events.append({"event_type": event_type, "payload": payload})


class _EmptyCapabilityRegistry:
    def get_handler(self, capability_id):
        return None


class _Plane:
    def __init__(self):
        self.capability_registry = _EmptyCapabilityRegistry()
        self.spec_registry = None
        self.run_stream_event_repository = _StubStreamRepo()


@pytest.mark.asyncio
async def test_missing_capability_handler_fails_run_with_reason_code(monkeypatch):
    calls = []

    async def fake_callback(run_id, status, artifact_ref=None, summary_ref=None):
        calls.append((run_id, status))

    monkeypatch.setattr("apps.cosa.worker.copilot_run.callback_company_result", fake_callback)

    mgr = _RecordingStreamMgr()
    await run_customer_support_copilot(
        _Plane(),
        mgr,
        {"run_id": "run_1", "workspace_id": "ws_1", "thread_ref": {"thread_id": "t1"}},
    )

    assert ("run_1", "failed") in calls
    failed = [e for e in mgr.events if e["event_type"] == "run.failed"]
    assert failed
    assert failed[-1]["payload"].get("reason_code") == "capability_not_registered"
