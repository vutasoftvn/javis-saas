import os
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from workforce.agents.domains.sales.action import SalesActionCapability
from workforce.agents.execution.n8n_bridge import dispatch_outbound_action, verify_hmac_signature


@pytest.mark.asyncio
async def test_dispatch_outbound_action_signs_and_posts():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        res = await dispatch_outbound_action(
            webhook_url="https://n8n.cosa.local/webhook/sales-outreach",
            webhook_secret="test-n8n-secret",
            action_type="sales.outreach",
            payload={"recipient_email": "founder@example.com", "channel": "email"},
        )

        assert res["success"] is True
        assert res["delivered"] is True
        assert res["status"] == "delivered_to_n8n"
        assert mock_post.called

        # Verify HMAC header was sent
        call_kwargs = mock_post.call_args[1]
        headers = call_kwargs["headers"]
        assert "X-COSA-Signature" in headers
        assert "X-COSA-Timestamp" in headers

        content = call_kwargs["content"]
        assert verify_hmac_signature("test-n8n-secret", content, headers["X-COSA-Timestamp"], headers["X-COSA-Signature"]) is True


@pytest.mark.asyncio
async def test_sales_action_capability_dispatch_outreach_with_webhook():
    mock_db = MagicMock()
    with patch.dict(os.environ, {
        "COSA_N8N_SALES_OUTREACH_WEBHOOK_URL": "https://n8n.cosa.local/webhook/outreach",
        "COSA_N8N_SALES_OUTREACH_SECRET": "test-secret-123",
    }), patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        drafts = [
            {"recipient_email": "alex@alphacorp.example", "recipient_name": "Alex", "subject": "Intro", "body": "Hello"}
        ]

        result = await SalesActionCapability.dispatch_outreach(
            db=mock_db,
            workspace_id=888888,
            drafts=drafts,
            is_approved=True,
        )

        assert result["status"] == "success"
        assert result["dispatched_count"] == 1
        assert result["receipts"][0]["delivered"] is True
        assert result["receipts"][0]["recipient"] == "alex@alphacorp.example"


@pytest.mark.asyncio
async def test_sales_action_capability_simulated_mode_when_no_webhook():
    mock_db = MagicMock()
    with patch.dict(os.environ, {}, clear=True):
        drafts = [
            {"recipient_email": "alex@alphacorp.example", "recipient_name": "Alex"}
        ]

        result = await SalesActionCapability.dispatch_outreach(
            db=mock_db,
            workspace_id=888888,
            drafts=drafts,
            is_approved=True,
        )

        assert result["status"] == "success"
        assert result["dispatched_count"] == 1
        assert result["receipts"][0]["status"] == "mock_delivered"
