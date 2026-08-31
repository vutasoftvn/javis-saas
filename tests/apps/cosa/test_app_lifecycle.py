"""Test cho apps/cosa/api/app.py — Phase 5 Composition Lifecycle
(docs/implementation/production-runtime-closure.md §10). Exit criteria:
app fail-fast ở startup nếu thiếu config; không còn code path tạo
CosaAgentPlane on first request; test lifecycle (start → healthy →
shutdown clean) pass.

Dùng `fastapi.testclient.TestClient` làm context manager — đây là công cụ
DUY NHẤT trong bộ test hiện có THẬT SỰ trigger ASGI lifespan protocol
(`httpx.ASGITransport` dùng ở các test khác không tự gửi lifespan.startup/
shutdown — xem test_vertical_slice_*/test_tenant_isolation.py, nơi
`create_cosa_app(plane=...)` gán thẳng `app.state.plane` để không phụ thuộc
lifespan có chạy hay không)."""
from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from fastapi.testclient import TestClient

from apps.cosa.api import app as app_module
from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane


def _in_memory_plane(**overrides):
    mock_client = AsyncMock(spec=CompanyServiceClient)
    kwargs = dict(
        company_client=mock_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
    kwargs.update(overrides)
    return build_cosa_agent_plane(**kwargs)


def test_start_healthy_shutdown_with_injected_plane():
    """start (lifespan chạy, không build gì vì plane đã inject) → healthy
    (/healthz trả "ok") → shutdown clean (không raise, TestClient context
    thoát bình thường)."""
    plane = _in_memory_plane()
    app = create_cosa_app(plane=plane)

    with TestClient(app) as client:
        assert app.state.plane is plane
        res = client.get("/healthz")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
    # Thoát context = lifespan shutdown đã chạy xong không raise.


def test_shutdown_does_not_close_injected_plane_clients():
    """Plane inject qua `plane=` (test/dev sở hữu vòng đời) — lifespan
    shutdown KHÔNG được tự ý đóng client của plane đó, chỉ đóng plane app tự
    build. `HttpControlPlaneSchedulerClient` thật có `aclose()`; dùng mock để
    verify KHÔNG bị gọi."""
    plane = _in_memory_plane()
    plane.tenant_policy_client = AsyncMock()
    app = create_cosa_app(plane=plane)

    with TestClient(app):
        pass

    plane.tenant_policy_client.aclose.assert_not_called()


def test_non_injected_lifespan_bootstraps_complete_runtime_registry(monkeypatch):
    """Production lifespan phải gọi full runtime bootstrap, không chỉ publish
    AgentSpec. Nếu mất call này, worker dispatch sẽ lại fail do pinned skill
    chưa có trong registry dù API đã healthy."""
    plane = _in_memory_plane()
    bootstrap = AsyncMock()

    monkeypatch.setattr(app_module, "build_cosa_agent_plane", lambda: plane)
    monkeypatch.setattr(app_module, "seed_cosa_runtime_specs", bootstrap)

    app = create_cosa_app()
    with TestClient(app):
        bootstrap.assert_awaited_once_with(
            spec_registry=plane.spec_registry,
            capability_registry=plane.capability_registry,
        )


def test_app_fails_fast_at_startup_when_config_missing():
    """Không inject plane, không có AGENT_DATABASE_URL/repository nào —
    build_cosa_agent_plane() raise RuntimeError NGAY ở lifespan startup, TRƯỚC
    khi app chuyển sang trạng thái phục vụ traffic. Đây chính là hành vi thay
    thế lazy singleton cũ (trước đây lỗi này chỉ lộ ra ở request ĐẦU TIÊN,
    sau khi app đã "healthy")."""
    env_backup = {
        k: os.environ.pop(k, None) for k in ("AGENT_DATABASE_URL", "DEEPSEEK_API_KEY")
    }
    try:
        app = create_cosa_app()  # không inject plane -> lifespan phải tự build
        with pytest.raises(RuntimeError, match="AGENT_DATABASE_URL"), TestClient(app):
            pytest.fail("Should not reach here — lifespan startup must fail first")
    finally:
        for k, v in env_backup.items():
            if v is not None:
                os.environ[k] = v


def test_liveness_is_always_ok_when_process_running():
    """`/live` chỉ phản ánh process còn sống — không phụ thuộc dependency,
    dùng cho probe "process crashed, restart container" (khác readiness)."""
    plane = _in_memory_plane()
    app = create_cosa_app(plane=plane)

    with TestClient(app) as client:
        res = client.get("/live")
        assert res.status_code == 200


def test_readiness_ok_with_fully_wired_plane():
    """`/ready` phải trả 200 khi plane đã wire đủ dependency cốt lõi (đúng
    hành vi cũ của `/healthz`, giờ `/healthz` delegate sang route này)."""
    plane = _in_memory_plane()
    app = create_cosa_app(plane=plane)

    with TestClient(app) as client:
        res = client.get("/ready")
        assert res.status_code == 200
        healthz_res = client.get("/healthz")
        assert healthz_res.status_code == 200


def test_readiness_reports_missing_dependencies():
    """`/ready` phải trả 503 khi plane thiếu dependency cốt lõi — khác hẳn
    `/healthz` cũ (luôn trả 200 "ok"/"not_ready" bất kể dependency thật có
    sẵn sàng hay không). Plane rỗng (`SimpleNamespace()`) mô phỏng 1 plane
    chưa wire đủ (thiếu spec_registry/kernel/...)."""
    app = create_cosa_app(plane=SimpleNamespace())
    with TestClient(app) as client:
        assert client.get("/ready").status_code == 503
        # /healthz phải delegate cùng logic — không còn trả 200 "not_ready".
        assert client.get("/healthz").status_code == 503


def test_no_lazy_plane_creation_on_first_request():
    """Exit criteria: không còn code path tạo CosaAgentPlane on first
    request. `get_cosa_plane()` (dependency) phải raise rõ ràng thay vì âm
    thầm tạo plane mới khi app.state.plane chưa được set — mô phỏng tình
    huống dùng sai (app chưa qua lifespan startup, vd raw ASGITransport)."""
    from fastapi import FastAPI, Request

    from apps.cosa.api.routes import get_cosa_plane

    bare_app = FastAPI()  # KHÔNG set app.state.plane — giống app chưa qua lifespan

    scope = {"type": "http", "app": bare_app, "headers": []}
    request = Request(scope)

    with pytest.raises(RuntimeError, match=r"app\.state\.plane"):
        get_cosa_plane(request)
