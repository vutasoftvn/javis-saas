import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_workspace_member
from app.core.snowflake import generate_snowflake_id
from app.automations.models import AutomationRun
from app.automations.runtime.adapters.mock import MockAutomationProvider
from app.automations.runtime.adapters.n8n import (
    N8nAdapter,
    generate_hmac_signature,
    verify_hmac_signature,
)
from app.automations.runtime.types import AutomationRequest


@pytest.mark.asyncio
async def test_mock_automation_provider_contract():
    provider = MockAutomationProvider()

    health = await provider.health()
    assert health.status == "healthy"
    assert health.provider == "mock"

    caps = await provider.list_capabilities()
    assert "system.telegram_notification" in caps

    req = AutomationRequest(
        automation_key="system.telegram_notification",
        execution_id="exec_123",
        workspace_id=999,
        payload={"message": "Lead qualified"},
    )
    result = await provider.execute(req)
    assert result.status == "completed"
    assert result.provider_execution_id == "mock_exec_exec_123"

    status_res = await provider.get_status(result.provider_execution_id)
    assert status_res.status == "succeeded"


def test_hmac_signature_generation_and_verification():
    secret = "test-secret-key-123"
    payload = json.dumps({"status": "succeeded", "execution_id": "123"})
    timestamp = "2026-08-14T12:00:00Z"

    sig = generate_hmac_signature(secret, payload, timestamp)
    assert isinstance(sig, str)
    assert len(sig) == 64

    # Valid check
    assert verify_hmac_signature(secret, payload, timestamp, sig) is True

    # Tampered payload check
    assert verify_hmac_signature(secret, payload + "tampered", timestamp, sig) is False

    # Tampered timestamp check
    assert verify_hmac_signature(secret, payload, "2026-08-14T12:01:00Z", sig) is False


@pytest.mark.asyncio
async def test_n8n_adapter_execution():
    adapter = N8nAdapter(base_url="http://n8n.test", api_key="secret-key")

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"execution_id": "n8n_exec_999"}'
        mock_response.json.return_value = {"execution_id": "n8n_exec_999"}
        mock_post.return_value = mock_response

        req = AutomationRequest(
            automation_key="sales.followup_email",
            execution_id="exec_888",
            workspace_id=12345,
            payload={"lead_id": 1},
        )
        res = await adapter.execute(req)
        assert res.status == "running"
        assert res.provider_execution_id == "n8n_exec_999"


def test_automations_rest_endpoints(client: TestClient):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    member = MagicMock()
    member.workspace_id = ws_id
    member.user_id = user_id

    app.dependency_overrides[get_current_workspace_member] = lambda: member

    try:
        from app.db.session import get_db
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        app.dependency_overrides[get_db] = lambda: mock_db

        # 1. Health
        res_health = client.get("/api/v1/automations/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "healthy"

        # 2. Definitions Catalog
        res_defs = client.get("/api/v1/automations/definitions")
        assert res_defs.status_code == 200
        defs = res_defs.json()
        assert len(defs) >= 2
        assert any(d["automation_key"] == "system.telegram_notification" for d in defs)

        # 3. Execute
        res_exec = client.post(
            "/api/v1/automations/execute",
            json={
                "automation_key": "system.telegram_notification",
                "payload": {"text": "Hot lead detected"},
            },
        )
        assert res_exec.status_code == 200
        data = res_exec.json()
        assert data["automation_key"] == "system.telegram_notification"
        assert data["status"] in ("succeeded", "running")

    finally:
        app.dependency_overrides.pop(get_current_workspace_member, None)


def test_automations_callback_endpoint_with_hmac(client: TestClient):
    run_id = generate_snowflake_id()
    run = AutomationRun(
        id=run_id,
        workspace_id=generate_snowflake_id(),
        automation_key="sales.followup_email",
        status="running",
    )

    from app.db.session import get_db
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = run
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        timestamp = "2026-08-14T12:00:00Z"
        payload_data = {
            "execution_id": str(run_id),
            "provider_execution_id": "n8n_exec_555",
            "status": "succeeded",
            "result": {"email_sent": True},
        }
        body_str = json.dumps(payload_data)
        secret = "cosa-n8n-default-secret"
        sig = generate_hmac_signature(secret, body_str, timestamp)

        headers = {
            "X-COSA-Signature": sig,
            "X-COSA-Timestamp": timestamp,
            "Content-Type": "application/json",
        }

        res = client.post("/api/v1/automations/callback", content=body_str, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "accepted"
        assert data["verified"] is True
        assert data["run_id"] == str(run_id)

    finally:
        app.dependency_overrides.pop(get_db, None)
