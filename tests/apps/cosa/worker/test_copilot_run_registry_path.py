import pytest
from agent.capabilities.gateway import CapabilityGateway
from agent.capabilities.registry import CapabilityRegistry

from apps.cosa.worker.copilot_run import run_customer_support_copilot


class _StubStreamRepo: ...


class _RecordingStreamMgr:
    def __init__(self):
        self.events = []

    async def emit(
        self,
        repo,
        *,
        run_id,
        conversation_id,
        event_type,
        payload,
        correlation_id,
        activity_service=None,
        workspace_id=None,
        project_id=None,
    ):
        self.events.append({"event_type": event_type, "payload": payload})


class _EmptyCapabilityRegistry:
    def get_handler(self, capability_id):
        return None


class _Plane:
    def __init__(self):
        self.capability_registry = _EmptyCapabilityRegistry()
        # IA25 phần 2 — copilot_run.py gọi capability qua plane.gateway.execute()
        # (CapabilityGateway thật), không còn tự gọi capability_registry.get_handler()
        # trực tiếp. Dùng CapabilityGateway thật với registry RỖNG thật (không
        # phải stub tự chế) để "capability không tồn tại" đi qua đúng nhánh
        # thật ở Bước 1 của gateway, không giả lập hành vi của nó.
        self.gateway = CapabilityGateway(registry=CapabilityRegistry())
        self.spec_registry = None
        self.run_stream_event_repository = _StubStreamRepo()


@pytest.mark.asyncio
async def test_missing_capability_handler_fails_run_with_reason_code(monkeypatch):
    calls = []

    async def fake_callback(
        run_id, status, artifact_ref=None, summary_ref=None, reason_code=None, evidence_refs=None
    ):
        calls.append((run_id, status))

    monkeypatch.setattr("apps.cosa.worker.copilot_run.callback_company_result", fake_callback)

    mgr = _RecordingStreamMgr()
    await run_customer_support_copilot(
        _Plane(),
        mgr,
        {
            "run_id": "run_1",
            "workspace_id": "ws_1",
            "thread_ref": {"thread_id": "t1"},
            "delegation_token": "test-delegation-token",
        },
    )

    assert ("run_1", "failed") in calls
    failed = [e for e in mgr.events if e["event_type"] == "run.failed"]
    assert failed
    assert failed[-1]["payload"].get("reason_code") == "capability_gateway_failed"
    assert "not found in registry" in failed[-1]["payload"].get("error", "")
