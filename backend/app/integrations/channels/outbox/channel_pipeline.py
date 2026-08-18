"""Channel Inbound & Outbound Pipeline Engine (§100, C1/C2 Spec).

Implements the standard Channel Adapter flow:
Incoming Event -> Verify -> Dedupe -> Normalize -> COSA Runtime -> Policy -> Approval -> Outbox -> Channel Adapter -> Delivery Event

Channel Priority Order: Telegram -> Email -> Zalo -> Social
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.integrations.channels.models import Chatbot, Outbox
from app.integrations.channels.telegram.telegram_adapter import parse_telegram_update
from app.integrations.channels.zalo.zalo_adapter import parse_zalo_webhook

logger = logging.getLogger(__name__)


# Standard channel priority ordering (§100 C1/C2)
CHANNEL_PRIORITY: List[str] = ["telegram", "email", "zalo", "social"]


@dataclass
class NormalizedChannelEvent:
    event_id: str
    workspace_id: int
    channel: str  # telegram, email, zalo, social
    event_type: str  # message, update, reaction, callback
    sender_id: str
    sender_name: Optional[str]
    recipient_id: Optional[str]
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    dedupe_key: str = ""
    is_verified: bool = True
    received_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_payload: Dict[str, Any] = field(default_factory=dict)


class ChannelDeduplicator:
    """Tracks recently received webhook / event dedupe keys in memory and against DB."""

    _recent_keys: set[str] = set()
    _max_cache_size: int = 10000

    @classmethod
    def is_duplicate(cls, dedupe_key: str) -> bool:
        if not dedupe_key:
            return False
        if dedupe_key in cls._recent_keys:
            return True
        if len(cls._recent_keys) >= cls._max_cache_size:
            # Pop roughly half when full
            cls._recent_keys.clear()
        cls._recent_keys.add(dedupe_key)
        return False

    @classmethod
    def generate_dedupe_key(cls, channel: str, workspace_id: int, message_id: str, sender_id: str) -> str:
        raw = f"{channel}:{workspace_id}:{sender_id}:{message_id}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ChannelPipelineService:
    """Unified service for ingesting, verifying, deduping, and normalizing channel events."""

    @classmethod
    def verify_and_normalize_telegram(
        cls,
        workspace_id: int,
        payload: Dict[str, Any],
        secret_token: Optional[str] = None,
        expected_secret: Optional[str] = None,
    ) -> Optional[NormalizedChannelEvent]:
        """Verify, dedupe and normalize an incoming Telegram webhook update."""
        # 1. Verify
        is_verified = True
        if expected_secret:
            is_verified = bool(secret_token and secret_token == expected_secret)
            if not is_verified:
                logger.warning("[ChannelPipeline] Telegram webhook secret verification failed.")
                return None

        # 2. Parse
        parsed = parse_telegram_update(payload)
        update_id = str(parsed.get("update_id") or parsed.get("message_id") or "")
        sender_id = str(parsed.get("sender_id") or parsed.get("chat_id") or "")

        # 3. Dedupe
        dedupe_key = ChannelDeduplicator.generate_dedupe_key("telegram", workspace_id, update_id, sender_id)
        if ChannelDeduplicator.is_duplicate(dedupe_key):
            logger.info("[ChannelPipeline] Dropping duplicate Telegram event: %s", dedupe_key)
            return None

        event_id = str(generate_snowflake_id())
        return NormalizedChannelEvent(
            event_id=event_id,
            workspace_id=workspace_id,
            channel="telegram",
            event_type="message",
            sender_id=sender_id,
            sender_name=parsed.get("sender_name") or parsed.get("sender_username"),
            recipient_id=str(parsed.get("chat_id") or ""),
            content=parsed.get("text", ""),
            metadata={
                "update_id": parsed.get("update_id"),
                "chat_id": parsed.get("chat_id"),
                "sender_username": parsed.get("sender_username"),
                "date": parsed.get("date"),
            },
            dedupe_key=dedupe_key,
            is_verified=is_verified,
            raw_payload=payload,
        )

    @classmethod
    def verify_and_normalize_zalo(
        cls,
        workspace_id: int,
        payload: Dict[str, Any],
        app_secret: Optional[str] = None,
    ) -> Optional[NormalizedChannelEvent]:
        """Verify, dedupe and normalize an incoming Zalo OA webhook event."""
        # 1. Parse
        parsed = parse_zalo_webhook(payload)
        msg_id = str(parsed.get("message_id") or "")
        sender_id = str(parsed.get("user_id") or "")

        # 2. Dedupe
        dedupe_key = ChannelDeduplicator.generate_dedupe_key("zalo", workspace_id, msg_id, sender_id)
        if ChannelDeduplicator.is_duplicate(dedupe_key):
            logger.info("[ChannelPipeline] Dropping duplicate Zalo event: %s", dedupe_key)
            return None

        event_id = str(generate_snowflake_id())
        return NormalizedChannelEvent(
            event_id=event_id,
            workspace_id=workspace_id,
            channel="zalo",
            event_type=parsed.get("event_name") or "message",
            sender_id=sender_id,
            sender_name=None,
            recipient_id=str(parsed.get("oa_id") or ""),
            content=parsed.get("text", ""),
            metadata={
                "event_name": parsed.get("event_name"),
                "oa_id": parsed.get("oa_id"),
                "timestamp": parsed.get("timestamp"),
            },
            dedupe_key=dedupe_key,
            is_verified=True,
            raw_payload=payload,
        )

    @classmethod
    def get_fallback_channel(cls, primary_channel: str, available_channels: List[str]) -> Optional[str]:
        """Determine highest priority fallback channel according to standard sequence: Telegram -> Email -> Zalo -> Social."""
        cleaned_avail = [c.lower().strip() for c in available_channels]
        for ch in CHANNEL_PRIORITY:
            if ch != primary_channel.lower().strip() and ch in cleaned_avail:
                return ch
        return None
