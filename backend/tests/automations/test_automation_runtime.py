import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from main import app
from core.auth import get_current_workspace_member
from core.snowflake import generate_snowflake_id
from workforce.automation.models import AutomationDefinition, AutomationRun
from workforce.automation.runtime.adapters.mock import MockAutomationProvider
from workforce.automation.runtime.adapters.n8n import (
    N8nAdapter,
    generate_hmac_signature,
    verify_hmac_signature,
)
from workforce.automation.runtime.types import AutomationRequest


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


@pytest.mark.asyncio
async def test_n8n_adapter_get_status_without_api_key_is_honest_about_it():
    adapter = N8nAdapter(base_url="http://n8n.test")  # no api_key
    status_res = await adapter.get_status("exec_1")
    assert status_res.status == "running"
    assert status_res.error is not None and "N8N_API_KEY" in status_res.error


@pytest.mark.asyncio
async def test_n8n_adapter_get_status_maps_finished_and_error():
    adapter = N8nAdapter(base_url="http://n8n.test", api_key="secret-key")

    with patch("httpx.AsyncClient.get") as mock_get:
        finished_ok = MagicMock()
        finished_ok.status_code = 200
        finished_ok.json.return_value = {"finished": True, "data": {"resultData": {}}}
        mock_get.return_value = finished_ok

        res = await adapter.get_status("exec_ok")
        assert res.status == "succeeded"

        finished_err = MagicMock()
        finished_err.status_code = 200
        finished_err.json.return_value = {"finished": True, "data": {"resultData": {"error": "boom"}}}
        mock_get.return_value = finished_err

        res_err = await adapter.get_status("exec_err")
        assert res_err.status == "failed"
        assert res_err.error == "boom"

        not_found = MagicMock()
        not_found.status_code = 404
        mock_get.return_value = not_found

        res_404 = await adapter.get_status("exec_missing")
        assert res_404.status == "failed"


@pytest.mark.asyncio
async def test_n8n_adapter_cancel_raises_instead_of_silently_no_op():
    adapter = N8nAdapter(base_url="http://n8n.test", api_key="secret-key")
    with pytest.raises(NotImplementedError):
        await adapter.cancel("exec_1")


def test_automations_rest_endpoints(client: TestClient):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    member = MagicMock()
    member.workspace_id = ws_id
    member.user_id = user_id

    app.dependency_overrides[get_current_workspace_member] = lambda: member

    seeded_defs = [
        AutomationDefinition(
            id=generate_snowflake_id(),
            automation_key="system.telegram_notification",
            name="Telegram Notification",
            domain="system",
            provider="n8n",
            risk_level="low",
            approval_mode="none",
        ),
        AutomationDefinition(
            id=generate_snowflake_id(),
            automation_key="sales.followup_email",
            name="Sales Follow-up Email",
            domain="sales",
            provider="n8n",
            risk_level="medium",
            approval_mode="required",
        ),
    ]

    try:
        from db.session import get_db

        def query_mock(model):
            m = MagicMock()
            m.filter.return_value = m
            if model is AutomationDefinition:
                m.all.return_value = seeded_defs
                m.first.return_value = seeded_defs[0]
            return m

        mock_db = MagicMock()
        mock_db.query.side_effect = query_mock
        app.dependency_overrides[get_db] = lambda: mock_db

        # 1. Health
        res_health = client.get("/api/v1/automations/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "healthy"

        # 2. Definitions Catalog (from real seeded rows, no hardcoded fallback anymore)
        res_defs = client.get("/api/v1/automations/definitions")
        assert res_defs.status_code == 200
        defs = res_defs.json()
        assert len(defs) == 2
        assert any(d["automation_key"] == "system.telegram_notification" for d in defs)

        # 3. Execute a no-approval-needed automation
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

    from db.session import get_db
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = run
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()
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


def test_automations_callback_rejects_unsigned_and_invalid_signature(client: TestClient):
    run_id = generate_snowflake_id()
    run = AutomationRun(
        id=run_id,
        workspace_id=generate_snowflake_id(),
        automation_key="sales.followup_email",
        status="running",
    )

    from db.session import get_db
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = run
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        from datetime import datetime, timezone
        payload_data = {
            "execution_id": str(run_id),
            "provider_execution_id": "n8n_exec_555",
            "status": "succeeded",
            "result": {"email_sent": True},
        }
        body_str = json.dumps(payload_data)

        # No signature headers at all -> must be rejected, never applied.
        res_missing = client.post("/api/v1/automations/callback", content=body_str)
        assert res_missing.status_code == 401

        # Wrong signature -> must be rejected.
        timestamp = datetime.now(timezone.utc).isoformat()
        res_bad_sig = client.post(
            "/api/v1/automations/callback",
            content=body_str,
            headers={"X-COSA-Signature": "deadbeef", "X-COSA-Timestamp": timestamp},
        )
        assert res_bad_sig.status_code == 401

        # Correct signature but stale timestamp -> replay protection must reject it.
        secret = "cosa-n8n-default-secret"
        stale_timestamp = "2020-01-01T00:00:00Z"
        stale_sig = generate_hmac_signature(secret, body_str, stale_timestamp)
        res_stale = client.post(
            "/api/v1/automations/callback",
            content=body_str,
            headers={"X-COSA-Signature": stale_sig, "X-COSA-Timestamp": stale_timestamp},
        )
        assert res_stale.status_code == 401

        # Run must remain untouched by any of the rejected attempts above.
        assert run.status == "running"
        assert run.result_jsonb is None
    finally:
        app.dependency_overrides.pop(get_db, None)
