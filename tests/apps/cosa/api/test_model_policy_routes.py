"""Task 4 (plan 2026-09-07-local-first-model-routing) — HTTP-level test cho
`apps/cosa/api/model_policy_routes.py`: founder-only mutation, không bao giờ
trả lại API key trong response, test-connection có 2 tầng (structural +
live-call budget cố định), và GET policy hiển thị đúng precedence
(AGENT_PROFILE override > WORKSPACE default > system default)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from fastapi.testclient import TestClient

from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.models.repository import InMemoryModelRoutingRepository
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity


@pytest.fixture
def mock_company_client():
    client = AsyncMock(spec=CompanyServiceClient)
    client.get.return_value = {}
    client.post.return_value = {}
    return client


@pytest.fixture
def setup_env(mock_company_client):
    plane = build_cosa_agent_plane(
        company_client=mock_company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
        model_routing_repository=InMemoryModelRoutingRepository(),
    )
    application = create_cosa_app(plane=plane)
    override_authenticated_identity(
        application,
        principal_id="user:founder",
        platform_user_id="founder",
        workspace_id="ws-1",
        role_id="founder",
    )
    client = TestClient(application)
    return {"app": application, "plane": plane, "client": client}


def _as_member(app):
    override_authenticated_identity(
        app,
        principal_id="user:member",
        platform_user_id="member",
        workspace_id="ws-1",
        role_id="member",
    )


def _as_founder(app):
    override_authenticated_identity(
        app,
        principal_id="user:founder",
        platform_user_id="founder",
        workspace_id="ws-1",
        role_id="founder",
    )


# ── Founder/member authorization ──


def test_member_cannot_create_provider(setup_env):
    client: TestClient = setup_env["client"]
    _as_member(setup_env["app"])

    response = client.post(
        "/agent/settings/model-providers",
        json={"provider_type": "openrouter_api", "api_key": "sk-secret-value"},
    )
    assert response.status_code == 403


def test_member_cannot_test_provider(setup_env):
    client: TestClient = setup_env["client"]
    create_res = client.post(
        "/agent/settings/model-providers",
        json={"provider_type": "openrouter_api", "api_key": "sk-secret-value"},
    )
    profile_id = create_res.json()["data"]["profile_id"]

    _as_member(setup_env["app"])
    response = client.post(f"/agent/settings/model-providers/{profile_id}/test")
    assert response.status_code == 403


def test_member_cannot_set_policy(setup_env):
    client: TestClient = setup_env["client"]
    create_res = client.post(
        "/agent/settings/model-providers",
        json={"provider_type": "deepseek_api", "api_key": "sk-secret-value"},
    )
    profile_id = create_res.json()["data"]["profile_id"]

    _as_member(setup_env["app"])
    response = client.put(
        "/agent/settings/model-policies/operations",
        json={"primary_profile_id": profile_id, "fallback_profile_ids": []},
    )
    assert response.status_code == 403


def test_member_can_list_and_read_policy(setup_env):
    """Member được đọc status (không mutate) — đúng thiết kế
    "Member chỉ đọc status ... không xem hoặc thay secret"."""
    client: TestClient = setup_env["client"]
    client.post(
        "/agent/settings/model-providers",
        json={"provider_type": "deepseek_api", "api_key": "sk-secret-value"},
    )

    _as_member(setup_env["app"])
    list_res = client.get("/agent/settings/model-providers")
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) == 1

    policy_res = client.get("/agent/settings/model-policies/operations")
    assert policy_res.status_code == 200
    assert policy_res.json()["data"]["is_system_default"] is True


# ── Secret redaction ──


def test_create_provider_response_never_contains_api_key(setup_env):
    client: TestClient = setup_env["client"]
    plaintext_secret = "sk-super-secret-do-not-leak-123456"

    response = client.post(
        "/agent/settings/model-providers",
        json={"provider_type": "openrouter_api", "api_key": plaintext_secret},
    )
    assert response.status_code == 201
    assert "api_key" not in response.text
    assert plaintext_secret not in response.text
    data = response.json()["data"]
    assert data["credential_configured"] is True
    assert "api_key" not in data


def test_founder_policy_response_has_no_api_key(setup_env):
    client: TestClient = setup_env["client"]
    plaintext_secret = "sk-another-secret-value-987654"
    create_res = client.post(
        "/agent/settings/model-providers",
        json={
            "provider_type": "local_openai_compatible",
            "profile_id": "local-general",
            "model_id": "llama3",
            "api_key": plaintext_secret,
        },
    )
    assert create_res.status_code == 201
    assert plaintext_secret not in create_res.text

    response = client.put(
        "/agent/settings/model-policies/operations",
        json={"primary_profile_id": "local-general", "fallback_profile_ids": []},
    )
    assert response.status_code == 200
    assert "api_key" not in response.text
    assert plaintext_secret not in response.text


def test_stored_credential_ciphertext_never_equals_plaintext(setup_env):
    """Kiểm tra tận repository (không chỉ HTTP response) — plaintext không
    bao giờ nằm trong dữ liệu đã lưu."""
    client: TestClient = setup_env["client"]
    plaintext_secret = "sk-check-storage-layer-555"
    create_res = client.post(
        "/agent/settings/model-providers",
        json={"provider_type": "anthropic_api", "api_key": plaintext_secret},
    )
    profile_id = create_res.json()["data"]["profile_id"]

    plane = setup_env["plane"]
    import asyncio

    profile = asyncio.run(plane.model_routing_repository.get_profile("ws-1", profile_id))
    credential_store = plane._model_settings_credential_store
    ciphertext_b64 = asyncio.run(credential_store.raw_ciphertext_for_test(profile.credential_ref))
    assert plaintext_secret not in ciphertext_b64
    assert plaintext_secret.encode().hex() not in ciphertext_b64


# ── Provider CRUD ──


def test_create_provider_without_api_key_marks_not_configured(setup_env):
    client: TestClient = setup_env["client"]
    response = client.post(
        "/agent/settings/model-providers",
        json={"provider_type": "local_openai_compatible", "model_id": "llama3"},
    )
    assert response.status_code == 201
    assert response.json()["data"]["credential_configured"] is False


def test_list_providers_reflects_created_profiles(setup_env):
    client: TestClient = setup_env["client"]
    client.post(
        "/agent/settings/model-providers",
        json={"provider_type": "deepseek_api", "api_key": "k1"},
    )
    client.post(
        "/agent/settings/model-providers",
        json={"provider_type": "openai_api", "api_key": "k2"},
    )
    response = client.get("/agent/settings/model-providers")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 2


# ── Test-connection ──


def test_test_connection_unknown_profile_returns_404(setup_env):
    client: TestClient = setup_env["client"]
    response = client.post("/agent/settings/model-providers/does-not-exist/test")
    assert response.status_code == 404


def test_test_connection_missing_credential_fails_structural_tier(setup_env):
    """Provider yêu cầu credential (API-based) nhưng không có -> thất bại ở
    tầng 1 (structural), KHÔNG chạy live call."""
    client: TestClient = setup_env["client"]
    create_res = client.post(
        "/agent/settings/model-providers",
        json={"provider_type": "openai_api", "model_id": "gpt-4o-mini"},
    )
    profile_id = create_res.json()["data"]["profile_id"]

    response = client.post(f"/agent/settings/model-providers/{profile_id}/test")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["ok"] is False
    assert data["live_call_attempted"] is False


def test_test_connection_local_openai_compatible_attempts_live_call(setup_env):
    """Local endpoint không có server thật lắng nghe -> live call thất bại,
    nhưng đây LÀ tầng 2 thật sự (live_call_attempted=True) với budget cố định
    (max_tokens=1) — không phải suy luận client-side."""
    client: TestClient = setup_env["client"]
    create_res = client.post(
        "/agent/settings/model-providers",
        json={
            "provider_type": "local_openai_compatible",
            "model_id": "llama3",
            "base_url": "http://127.0.0.1:1",  # port không lắng nghe -> refuse nhanh
        },
    )
    profile_id = create_res.json()["data"]["profile_id"]

    response = client.post(f"/agent/settings/model-providers/{profile_id}/test")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["live_call_attempted"] is True
    assert data["ok"] is False


def test_test_connection_cli_provider_attempts_real_subprocess_call(setup_env, monkeypatch):
    """Final-review finding #2 regression: CLI provider test-connection PHẢI
    thực sự spawn `CliBridge` (không được suy luận `ok=True` chỉ vì dựng được
    `CliBridgeModel`). Trỏ `COSA_CLI_CLAUDE_PATH` sang 1 path CHẮC CHẮN không
    tồn tại (không phụ thuộc máy chạy test có cài `claude` CLI thật hay
    không) -> subprocess thất bại -> `ok=False`, nhưng `live_call_attempted`
    PHẢI là `True` (đã thực sự cố spawn), khác hẳn hành vi cũ
    (`live_call_attempted=False` không hề chạm subprocess)."""
    monkeypatch.setenv("COSA_CLI_CLAUDE_PATH", "/nonexistent/definitely-not-a-real-cli/claude")
    client: TestClient = setup_env["client"]
    create_res = client.post(
        "/agent/settings/model-providers",
        json={"provider_type": "claude_cli", "model_id": "claude-cli-default"},
    )
    profile_id = create_res.json()["data"]["profile_id"]

    response = client.post(f"/agent/settings/model-providers/{profile_id}/test")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["live_call_attempted"] is True
    assert data["ok"] is False


# ── Policy set/get, precedence ──


def test_set_policy_with_unknown_primary_profile_returns_400(setup_env):
    client: TestClient = setup_env["client"]
    response = client.put(
        "/agent/settings/model-policies/operations",
        json={"primary_profile_id": "ghost-profile", "fallback_profile_ids": []},
    )
    assert response.status_code == 400


def test_agent_override_takes_precedence_over_workspace_default(setup_env):
    client: TestClient = setup_env["client"]
    ws_default_res = client.post(
        "/agent/settings/model-providers",
        json={"provider_type": "deepseek_api", "profile_id": "ws-default", "api_key": "k"},
    )
    assert ws_default_res.status_code == 201
    override_res = client.post(
        "/agent/settings/model-providers",
        json={"provider_type": "openai_api", "profile_id": "ops-override", "api_key": "k2"},
    )
    assert override_res.status_code == 201

    set_ws = client.put(
        "/agent/settings/model-policies/_workspace_default",
        json={"primary_profile_id": "ws-default", "fallback_profile_ids": []},
    )
    assert set_ws.status_code == 200
    assert set_ws.json()["data"]["is_system_default"] is False

    # Trước khi có override riêng: "operations" thấy đúng workspace default.
    before = client.get("/agent/settings/model-policies/operations")
    assert before.json()["data"]["resolved_profile_id"] == "ws-default"

    set_override = client.put(
        "/agent/settings/model-policies/operations",
        json={"primary_profile_id": "ops-override", "fallback_profile_ids": []},
    )
    assert set_override.status_code == 200

    after = client.get("/agent/settings/model-policies/operations")
    assert after.json()["data"]["resolved_profile_id"] == "ops-override"

    # Agent khác không có override vẫn thấy workspace default (không bị đổi).
    other = client.get("/agent/settings/model-policies/finance")
    assert other.json()["data"]["resolved_profile_id"] == "ws-default"


def test_get_policy_returns_system_default_when_unconfigured(setup_env):
    client: TestClient = setup_env["client"]
    response = client.get("/agent/settings/model-policies/marketing")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_system_default"] is True
