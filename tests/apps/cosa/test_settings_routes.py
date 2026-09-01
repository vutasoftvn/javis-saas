from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
from agent.artifacts import InMemoryArtifactRepository
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.models import PublishedSpecRecord
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.vault.repository import InMemoryVaultRepository
from agent.workforce.repository import InMemoryWorkforceRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.workspace_settings_client import WorkspaceSettingsClientError
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    fake_active_tenant_policy_client,
)

GROWTH_HACKING_SKILL_ID = "growth_hacking"


class FakeWorkspaceSettingsClient:
    """Test double thay cho HTTP thật sang services/cosa — cho phép test
    khẳng định GET/PUT thật sự đọc/ghi qua client này (không tự lưu ở
    apps/cosa) mà không cần 1 Encore server thật chạy trong unit test."""

    def __init__(self) -> None:
        self._policies: dict[tuple[str, str], dict[str, Any]] = {}
        self.list_calls: list[str] = []
        self.put_calls: list[dict[str, Any]] = []
        self.raise_unavailable = False

    async def list_policies(self, *, workspace_id: str, bearer_token: str) -> list[dict[str, Any]]:
        self.list_calls.append(workspace_id)
        if self.raise_unavailable:
            raise WorkspaceSettingsClientError("control plane unreachable (fake)")
        return [p for (ws, _), p in self._policies.items() if ws == workspace_id]

    async def put_policy(
        self,
        *,
        workspace_id: str,
        skill_key: str,
        enabled: bool,
        config: dict[str, Any],
        bearer_token: str,
    ) -> dict[str, Any]:
        self.put_calls.append(
            {"workspace_id": workspace_id, "skill_key": skill_key, "enabled": enabled, "config": config}
        )
        if self.raise_unavailable:
            raise WorkspaceSettingsClientError("control plane unreachable (fake)")
        key = (workspace_id, skill_key)
        existing = self._policies.get(key)
        revision = (existing["revision"] + 1) if existing else 1
        saved = {
            "workspaceId": workspace_id,
            "skillKey": skill_key,
            "enabled": enabled,
            "config": config,
            "revision": revision,
            "updatedBy": "test_operator",
            "updatedAt": "2026-09-01T00:00:00+00:00",
        }
        self._policies[key] = saved
        return saved


def _publish_growth_hacking_skill(spec_registry: InMemorySpecRegistryRepository) -> None:
    asyncio.run(
        spec_registry.publish(
            PublishedSpecRecord(
                spec_kind="skill",
                spec_id=GROWTH_HACKING_SKILL_ID,
                version="1.0.0",
                definition_hash="test-hash-growth-hacking",
                content={
                    "name": "Growth Hacking",
                    "description": "Runs growth experiments",
                    "autonomy": {"ceiling": "L1_PROPOSE"},
                    "applicability": {"tags": ["growth", "leads"]},
                },
                status="published",
                publisher="cosa_platform",
            )
        )
    )


@pytest.fixture
def fake_settings_client() -> FakeWorkspaceSettingsClient:
    return FakeWorkspaceSettingsClient()


@pytest.fixture
def test_app(fake_settings_client: FakeWorkspaceSettingsClient):
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    spec_registry = InMemorySpecRegistryRepository()
    _publish_growth_hacking_skill(spec_registry)

    plane = build_cosa_agent_plane(
        company_client=mock_client,
        tenant_policy_client=fake_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=spec_registry,
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        workforce_repository=InMemoryWorkforceRepository(),
        vault_repository=InMemoryVaultRepository(),
        model=FakeSDKModel(),
        workspace_settings_client=fake_settings_client,
    )
    asyncio.run(seed_cosa_agent_specs(plane.spec_registry))
    return create_cosa_app(plane)


@pytest.mark.asyncio
async def test_skill_settings_shows_truthful_source(test_app) -> None:
    """GET trả danh mục skill từ registry, source authoritative là
    control_plane (không còn agent_db — enabled/config/revision đọc thật từ
    COSA Control Plane, registry chỉ cung cấp danh mục/metadata)."""
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/settings/skills")
        assert res.status_code == 200
        data = res.json()
        assert data["meta"]["sources"][0]["kind"] == "control_plane"
        assert isinstance(data["data"], list)
        growth = next(s for s in data["data"] if s["skillKey"] == GROWTH_HACKING_SKILL_ID)
        assert growth["installed"] is True
        assert growth["revision"] == 0


@pytest.mark.asyncio
async def test_skill_settings_registry_unavailable_returns_503_not_fake_empty_list(test_app) -> None:
    """Đây là bug đã phát hiện: registry lỗi trước đây bị nuốt (`except
    Exception: pass`) rồi trả `200 {data: [], source: agent_db}` — coi lỗi
    là "chưa có skill nào". Giờ PHẢI trả 503, không bao giờ echo thành công
    rỗng."""
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")

    async def _broken_list_all(spec_kind: str | None = None):
        raise RuntimeError("registry database connection lost")

    test_app.state.plane.spec_registry.list_all = _broken_list_all

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/settings/skills")
        assert res.status_code == 503
        body = res.json()
        assert body.get("data") is None or body.get("data") != []
        assert "detail" in body


@pytest.mark.asyncio
async def test_update_skill_setting_persists_via_control_plane_and_increments_revision(
    test_app, fake_settings_client: FakeWorkspaceSettingsClient
) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res1 = await client.put(
            f"/agent/settings/skills/{GROWTH_HACKING_SKILL_ID}",
            json={"enabled": True, "config": {"max_autonomy": "supervised"}},
        )
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["meta"]["data_state"] == "populated"
        assert data1["meta"]["sources"][0]["kind"] == "control_plane"
        assert data1["data"]["skillKey"] == GROWTH_HACKING_SKILL_ID
        assert data1["data"]["installed"] is True
        assert data1["data"]["revision"] == 1

        res2 = await client.put(
            f"/agent/settings/skills/{GROWTH_HACKING_SKILL_ID}",
            json={"enabled": False, "config": {}},
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["data"]["revision"] == 2
        assert data2["data"]["installed"] is False

    # Client thật sự được gọi (apps/cosa không tự lưu policy).
    assert len(fake_settings_client.put_calls) == 2


@pytest.mark.asyncio
async def test_update_skill_setting_rejects_unknown_skill(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.put(
            "/agent/settings/skills/no_such_skill",
            json={"enabled": True, "config": {}},
        )
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_update_skill_setting_requires_operator_role(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="member")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.put(
            f"/agent/settings/skills/{GROWTH_HACKING_SKILL_ID}",
            json={"enabled": True, "config": {}},
        )
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_update_skill_setting_control_plane_unavailable_returns_503(
    test_app, fake_settings_client: FakeWorkspaceSettingsClient
) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    fake_settings_client.raise_unavailable = True

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.put(
            f"/agent/settings/skills/{GROWTH_HACKING_SKILL_ID}",
            json={"enabled": True, "config": {}},
        )
        assert res.status_code == 503
        assert res.json().get("data") != {}
