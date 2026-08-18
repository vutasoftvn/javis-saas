import pytest
from app.integrations.channels.outbox.channel_pipeline import (
    ChannelDeduplicator,
    ChannelPipelineService,
    CHANNEL_PRIORITY,
)


def test_channel_priority_order():
    """Invariant check: Priority is Telegram -> Email -> Zalo -> Social."""
    assert CHANNEL_PRIORITY == ["telegram", "email", "zalo", "social"]

    fallback = ChannelPipelineService.get_fallback_channel("zalo", ["telegram", "zalo", "email"])
    assert fallback == "telegram"

    fallback2 = ChannelPipelineService.get_fallback_channel("telegram", ["email", "zalo"])
    assert fallback2 == "email"


def test_channel_deduplicator():
    ChannelDeduplicator._recent_keys.clear()
    key = ChannelDeduplicator.generate_dedupe_key("telegram", 100, "msg_123", "sender_456")
    
    assert not ChannelDeduplicator.is_duplicate(key)
    # Second time must be detected as duplicate
    assert ChannelDeduplicator.is_duplicate(key)


def test_verify_and_normalize_telegram():
    ChannelDeduplicator._recent_keys.clear()
    payload = {
        "update_id": 99999,
        "message": {
            "message_id": 1234,
            "from": {"id": 555, "first_name": "Test", "last_name": "User", "username": "testuser"},
            "chat": {"id": 888, "type": "private"},
            "text": "Hello COSA OS",
            "date": 1700000000,
        }
    }

    event = ChannelPipelineService.verify_and_normalize_telegram(
        workspace_id=1,
        payload=payload,
    )
    assert event is not None
    assert event.channel == "telegram"
    assert event.content == "Hello COSA OS"
    assert event.sender_id == "555"
    assert event.recipient_id == "888"
    assert event.is_verified is True

    # Duplicate payload should return None
    event_dup = ChannelPipelineService.verify_and_normalize_telegram(
        workspace_id=1,
        payload=payload,
    )
    assert event_dup is None


def test_verify_and_normalize_zalo():
    ChannelDeduplicator._recent_keys.clear()
    payload = {
        "event_name": "user_send_text",
        "app_id": "123456",
        "sender": {"id": "zalo_user_111"},
        "recipient": {"id": "oa_222"},
        "message": {"text": "Xin chào Zalo", "msg_id": "msg_999"},
        "timestamp": "1700000000",
    }

    event = ChannelPipelineService.verify_and_normalize_zalo(
        workspace_id=2,
        payload=payload,
    )
    assert event is not None
    assert event.channel == "zalo"
    assert event.event_type == "user_send_text"
    assert event.content == "Xin chào Zalo"
    assert event.sender_id == "zalo_user_111"
    assert event.recipient_id == "oa_222"
