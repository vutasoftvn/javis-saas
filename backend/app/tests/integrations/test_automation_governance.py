import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.workforce.automation.models import AutomationDefinition, AutomationRun
from app.integrations.channels.models import Chatbot, EmailApproval, Outbox
from app.integrations.workflows.n8n_gateway_service import (
    dispatch_n8n_workflow,
    generate_hmac_signature,
    handle_n8n_callback,
)
from app.integrations.channels.outbox.outbox_processor import process_single_outbox_item
from app.core.snowflake import generate_snowflake_id


@pytest.mark.asyncio
async def test_n8n_gateway_requires_approval_for_governed_automation():
    """Ensure n8n workflow dispatch triggers approval creation if definition approval_mode is required."""
    mock_db = MagicMock()
    auto_def = AutomationDefinition(
        id=generate_snowflake_id(),
        automation_key="sales.send_mass_campaign",
        name="Mass Outreach",
        domain="sales",
        provider="n8n",
        risk_level="high",
        approval_mode="explicit",
        enabled=True,
    )

    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.first.side_effect = [auto_def, None]
    mock_db.query.return_value = q

    res = await dispatch_n8n_workflow(
        db=mock_db,
        workspace_id=1,
        automation_key="sales.send_mass_campaign",
        payload={"recipients": 500},
    )

    assert res["status"] == "approval_required"
    assert "approval_id" in res
    assert res["automation_key"] == "sales.send_mass_campaign"


def test_n8n_callback_hmac_verification():
    """Ensure callback fails if HMAC signature is invalid."""
    mock_db = MagicMock()
    run_id = generate_snowflake_id()
    run = AutomationRun(
        id=run_id,
        workspace_id=1,
        automation_key="test_key",
        provider="n8n",
        status="running",
        risk_level="low",
    )
    mock_db.query.return_value.filter.return_value.first.return_value = run

    payload = {"execution_id": str(run_id), "status": "succeeded", "result": {"ok": True}}
    body_bytes = json.dumps(payload).encode("utf-8")
    valid_sig = generate_hmac_signature(body_bytes, "cosa-n8n-default-secret")

    # Valid callback
    res = handle_n8n_callback(
        db=mock_db,
        run_id=run_id,
        payload=payload,
        raw_body_bytes=body_bytes,
        signature_header=valid_sig,
    )
    assert res["status"] == "success"
    assert res["run_status"] == "succeeded"

    # Invalid signature should raise PermissionError
    with pytest.raises(PermissionError):
        handle_n8n_callback(
            db=mock_db,
            run_id=run_id,
            payload=payload,
            raw_body_bytes=body_bytes,
            signature_header="sha256=invalid_hash",
        )


@pytest.mark.asyncio
async def test_outbox_zalo_fallback_to_telegram():
    """When Zalo delivery fails, outbox attempts fallback to Telegram if available."""
    mock_db = MagicMock()
    zalo_bot = Chatbot(
        id=generate_snowflake_id(),
        workspace_id=1,
        name="Zalo Bot",
        channel="zalo",
        channel_config_jsonb={"access_token": "mock_zalo_token", "is_enabled": True},
    )
    tg_bot = Chatbot(
        id=generate_snowflake_id(),
        workspace_id=1,
        name="Telegram Bot",
        channel="telegram",
        channel_config_jsonb={"bot_token": "mock_tg_token", "is_enabled": True},
    )

    q = MagicMock()
    q.filter.return_value.first.side_effect = [zalo_bot, tg_bot]
    mock_db.query.return_value = q

    outbox_item = Outbox(
        id=generate_snowflake_id(),
        workspace_id=1,
        channel="zalo",
        payload_jsonb={
            "user_id": "zalo_123",
            "telegram_chat_id": "tg_456",
            "message": "Hello via Fallback",
            "fallback_channel": "telegram",
        },
        status="pending",
    )

    with patch("app.integrations.channels.outbox.outbox_processor.send_zalo_oa_message", side_effect=Exception("Zalo token expired")):
        with patch("app.integrations.channels.outbox.outbox_processor.send_telegram_message", new_callable=AsyncMock) as mock_tg:
            mock_tg.return_value = {"status": "sent", "message_id": 999}
            ok = await process_single_outbox_item(mock_db, outbox_item)
            assert ok is True
            assert outbox_item.status == "fallback_sent"
            assert outbox_item.payload_jsonb.get("fallback_used") == "telegram"


@pytest.mark.asyncio
async def test_outbox_email_resend_actually_sends_before_marking_sent():
    """Outbox channel=email phải gọi provider Resend thật trước khi được đánh dấu 'sent'.

    Trước fix, nhánh này set status='sent' ngay lập tức mà không gọi provider nào -
    Founder thấy 'đã gửi' trong khi thư chưa hề rời hệ thống.
    """
    mock_db = MagicMock()
    approval = EmailApproval(
        id=generate_snowflake_id(),
        workspace_id=1,
        provider="resend",
        to_email="lead@example.com",
        subject="Demo",
        body="Xin chào",
        status="approved",
    )
    mock_db.query.return_value.filter.return_value.first.return_value = approval

    outbox_item = Outbox(
        id=generate_snowflake_id(),
        workspace_id=1,
        channel="email",
        payload_jsonb={
            "approval_id": str(approval.id),
            "to_email": approval.to_email,
            "subject": approval.subject,
            "provider": "resend",
            "body": approval.body,
        },
        status="pending",
    )

    fake_provider = MagicMock()
    fake_provider.send_email = AsyncMock(return_value={"success": True, "id": "resend-msg-123"})

    with patch(
        "app.integrations.channels.email.providers.resend_provider.build_resend_client",
        return_value=fake_provider,
    ):
        ok = await process_single_outbox_item(mock_db, outbox_item)

    assert ok is True
    fake_provider.send_email.assert_awaited_once()
    assert outbox_item.status == "sent"
    assert outbox_item.payload_jsonb.get("provider_message_id") == "resend-msg-123"
    # EmailApproval song song phải đồng bộ, không được kẹt ở 'approved' mãi mãi.
    assert approval.status == "sent"


@pytest.mark.asyncio
async def test_outbox_email_provider_failure_marks_failed_not_sent():
    """Nếu provider gửi thư thật báo lỗi, Outbox phải là 'failed', không được là 'sent'."""
    mock_db = MagicMock()
    approval = EmailApproval(
        id=generate_snowflake_id(),
        workspace_id=1,
        provider="resend",
        to_email="lead@example.com",
        subject="Demo",
        body="Xin chào",
        status="approved",
    )
    mock_db.query.return_value.filter.return_value.first.return_value = approval

    outbox_item = Outbox(
        id=generate_snowflake_id(),
        workspace_id=1,
        channel="email",
        payload_jsonb={"approval_id": str(approval.id), "provider": "resend"},
        status="pending",
    )

    fake_provider = MagicMock()
    fake_provider.send_email = AsyncMock(side_effect=Exception("Resend API 401 invalid key"))

    with patch(
        "app.integrations.channels.email.providers.resend_provider.build_resend_client",
        return_value=fake_provider,
    ):
        ok = await process_single_outbox_item(mock_db, outbox_item)

    assert ok is False
    assert outbox_item.status == "failed"
    assert "Resend API 401" in outbox_item.payload_jsonb.get("last_error", "")
    assert approval.status == "failed"


@pytest.mark.asyncio
async def test_outbox_email_gmail_draft_send_calls_real_client():
    """Provider Gmail (mặc định) phải gọi send_draft thật trước khi đánh dấu 'sent'."""
    mock_db = MagicMock()
    approval = EmailApproval(
        id=generate_snowflake_id(),
        workspace_id=1,
        provider="gmail",
        draft_id="draft-abc",
        to_email="lead@example.com",
        subject="Demo",
        body="Xin chào",
        status="approved",
    )
    mock_db.query.return_value.filter.return_value.first.return_value = approval

    outbox_item = Outbox(
        id=generate_snowflake_id(),
        workspace_id=1,
        channel="email",
        payload_jsonb={"approval_id": str(approval.id)},
        status="pending",
    )

    fake_gmail_client = MagicMock()
    fake_gmail_client.send_draft = AsyncMock(return_value={"id": "gmail-msg-1"})

    with patch(
        "app.integrations.channels.google.google_connection_service.build_gmail_client",
        new_callable=AsyncMock,
        return_value=fake_gmail_client,
    ):
        ok = await process_single_outbox_item(mock_db, outbox_item)

    assert ok is True
    fake_gmail_client.send_draft.assert_awaited_once_with("draft-abc")
    assert outbox_item.status == "sent"
    assert approval.status == "sent"


@pytest.mark.asyncio
@pytest.mark.parametrize("channel", ["hub_approval", "marketing_action", "n8n"])
async def test_outbox_channel_without_real_provider_marks_failed(channel):
    """Chưa có provider gửi thật nào nối cho các kênh này -> phải 'failed', không được nói dối 'sent'."""
    mock_db = MagicMock()
    outbox_item = Outbox(
        id=generate_snowflake_id(),
        workspace_id=1,
        channel=channel,
        payload_jsonb={},
        status="pending",
    )

    ok = await process_single_outbox_item(mock_db, outbox_item)

    assert ok is False
    assert outbox_item.status == "failed"
