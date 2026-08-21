import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from core.snowflake import generate_snowflake_id
from db.models import WorkspaceMember
from integrations.channels.models import Outbox, Chatbot
from workforce.automation.models import AutomationRun, AutomationCallback
from integrations.channels.outbox.outbox_processor import (
    list_outbox_items,
    retry_outbox_item,
    process_outbox_batch_sync,
)
from integrations.channels.telegram.telegram_adapter import parse_telegram_update
from integrations.channels.zalo.zalo_adapter import parse_zalo_webhook
from integrations.workflows.n8n_gateway_service import (
    generate_hmac_signature,
    verify_hmac_signature,
    handle_n8n_callback,
)
from integrations.channels.outbox.outbox_router import get_outbox


def _mock_query():
    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.all.return_value = []
    q.first.return_value = None
    return q


def test_outbox_cross_tenant_forbidden():
    """Verify that user cannot access outbox of another workspace."""
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = generate_snowflake_id()

    other_ws_id = generate_snowflake_id()
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        get_outbox(workspace_id=other_ws_id, status=None, limit=50, member=member, db=db)

    assert exc_info.value.status_code == 403


def test_telegram_update_parser():
    """Verify parsing of Telegram inbound webhook message."""
    payload = {
        "update_id": 123456789,
        "message": {
            "message_id": 42,
            "from": {"id": 999888, "first_name": "Antigravity", "last_name": "Dev", "username": "antigravity_bot"},
            "chat": {"id": 100200300, "type": "private"},
            "date": 1723789000,
            "text": "Báo cáo doanh số ngày hôm nay",
        }
    }

    parsed = parse_telegram_update(payload)
    assert parsed["update_id"] == 123456789
    assert parsed["chat_id"] == "100200300"
    assert parsed["sender_name"] == "Antigravity Dev"
    assert parsed["text"] == "Báo cáo doanh số ngày hôm nay"


def test_zalo_webhook_parser():
    """Verify parsing of Zalo OA inbound webhook message."""
    payload = {
        "app_id": "1234567890123456",
        "event_name": "user_send_text_message",
        "sender": {"id": "zalo_user_789"},
        "recipient": {"id": "zalo_oa_123"},
        "message": {"msg_id": "msg_001", "text": "Xin tư vấn gói sản phẩm"},
        "timestamp": "1723789000000",
    }

    parsed = parse_zalo_webhook(payload)
    assert parsed["event_name"] == "user_send_text_message"
    assert parsed["user_id"] == "zalo_user_789"
    assert parsed["text"] == "Xin tư vấn gói sản phẩm"


def test_n8n_hmac_signature_verification():
    """Verify HMAC SHA-256 generation and verification."""
    secret = "cosa-n8n-super-secret"
    data = b'{"status":"succeeded","result":{"synced":true}}'

    sig = generate_hmac_signature(data, secret)
    assert sig.startswith("sha256=")

    # Valid
    assert verify_hmac_signature(data, sig, secret) is True
    # Invalid secret
    assert verify_hmac_signature(data, sig, "wrong-secret") is False
    # Altered body
    assert verify_hmac_signature(b'{"status":"failed"}', sig, secret) is False


def test_n8n_callback_updates_run():
    """Verify n8n callback updates run status and creates callback audit log."""
    run_id = generate_snowflake_id()
    secret = "test-secret"
    db = MagicMock()

    mock_run = MagicMock(spec=AutomationRun)
    mock_run.id = run_id
    mock_run.status = "running"

    query = _mock_query()
    query.first.return_value = mock_run
    db.query.return_value = query

    payload = {
        "provider_execution_id": "n8n_exec_001",
        "status": "succeeded",
        "result": {"rows_created": 5},
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = generate_hmac_signature(raw_body, secret)

    res = handle_n8n_callback(
        db=db,
        run_id=run_id,
        payload=payload,
        raw_body_bytes=raw_body,
        signature_header=sig,
        secret_key=secret,
    )

    assert res["status"] == "success"
    assert res["run_status"] == "succeeded"
    assert res["verified"] is True
    assert db.commit.called
