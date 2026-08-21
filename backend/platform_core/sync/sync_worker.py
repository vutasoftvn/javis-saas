"""Platform Sync Worker for COSA Hybrid Architecture (Phase 2).

Dispatches pending outbox events to Supabase Central and processes incoming inbox events.
Specification: COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md (Section 16, 17, 31)
"""
from datetime import datetime, timedelta
import logging
from typing import Any, Callable, Dict, List, Optional
import httpx
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from platform_core.sync.models import PlatformOutbox, PlatformInbox

logger = logging.getLogger(__name__)


class PlatformSyncWorker:
    """Worker responsible for reliable event ingestion and synchronization."""

    def __init__(
        self,
        central_api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        custom_http_client: Optional[Callable[[List[Dict[str, Any]]], Dict[str, Any]]] = None,
    ):
        self.central_api_url = central_api_url or "http://localhost:8000/api/v1/platform/sync/ingest"
        self.api_key = api_key
        self.custom_http_client = custom_http_client

    def calculate_backoff_seconds(self, retry_count: int) -> int:
        """Exponential backoff with cap: 5s, 10s, 20s, 40s... max 3600s (1 hour)."""
        return min(3600, (2 ** retry_count) * 5)

    def dispatch_events_to_central(
        self,
        envelopes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Sends batch of event envelopes to Central Ingestion API."""
        if self.custom_http_client:
            return self.custom_http_client(envelopes)

        headers = {
            "Content-Type": "application/json",
            "X-Platform-Source": "cosa_local_worker",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                self.central_api_url,
                json={"events": envelopes},
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    def process_outbox_batch(self, db: Session, batch_size: int = 50) -> int:
        """Pulls pending outbox events, dispatches to Central, and handles ACKs/backoff."""
        now = datetime.utcnow()
        stmt = (
            select(PlatformOutbox)
            .where(
                and_(
                    PlatformOutbox.status.in_(["pending", "failed"]),
                    or_(
                        PlatformOutbox.next_retry_at.is_(None),
                        PlatformOutbox.next_retry_at <= now,
                    ),
                )
            )
            .order_by(PlatformOutbox.created_at.asc())
            .limit(batch_size)
        )
        
        events: List[PlatformOutbox] = list(db.scalars(stmt).all())
        if not events:
            return 0

        # Build payload batch
        batch_envelopes = []
        for ev in events:
            batch_envelopes.append({
                "event_id": ev.event_id,
                "company_id": ev.company_id,
                "project_id": ev.aggregate_id if ev.aggregate_type == "project" else None,
                "event_type": ev.event_type,
                "classification": ev.classification,
                "payload": ev.payload,
                "occurred_at": ev.created_at.isoformat(),
                "schema_version": 1,
            })

        try:
            # Mark processing
            for ev in events:
                ev.status = "processing"
            db.flush()

            # Dispatch
            result = self.dispatch_events_to_central(batch_envelopes)
            
            # Central response maps event_id -> success
            ack_map: Dict[str, bool] = result.get("acknowledged", {})
            
            processed_count = 0
            for ev in events:
                is_acknowledged = ack_map.get(ev.event_id, True) # Default to true if batch succeeded
                if is_acknowledged:
                    ev.status = "acknowledged"
                    ev.sent_at = datetime.utcnow()
                    ev.acknowledged_at = datetime.utcnow()
                    ev.last_error = None
                    processed_count += 1
                else:
                    ev.retry_count += 1
                    ev.status = "failed" if ev.retry_count < ev.max_retries else "abandoned"
                    ev.last_error = "Rejected or unacknowledged by central"
                    backoff = self.calculate_backoff_seconds(ev.retry_count)
                    ev.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff)

            db.commit()
            logger.info(f"Processed {processed_count}/{len(events)} outbox events successfully")
            return processed_count

        except Exception as exc:
            db.rollback()
            logger.warning(f"Failed to dispatch outbox batch: {exc}")
            # Update retry counts and backoff timestamps
            for ev in events:
                ev.retry_count += 1
                ev.status = "failed" if ev.retry_count < ev.max_retries else "abandoned"
                ev.last_error = str(exc)
                backoff = self.calculate_backoff_seconds(ev.retry_count)
                ev.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff)
            db.commit()
            return 0

    def process_inbox_batch(self, db: Session, batch_size: int = 50) -> int:
        """Processes incoming events from Central (e.g. form submissions, entitlement notifications)."""
        stmt = (
            select(PlatformInbox)
            .where(PlatformInbox.status == "pending")
            .order_by(PlatformInbox.received_at.asc())
            .limit(batch_size)
        )
        inbox_items: List[PlatformInbox] = list(db.scalars(stmt).all())
        if not inbox_items:
            return 0

        processed = 0
        for item in inbox_items:
            try:
                # Event dispatch logic based on event_type
                if item.event_type == "form.submission_received":
                    # Form submission processing hook (e.g. creating/updating local CRM lead)
                    logger.info(f"Processing inbox form submission event {item.event_id}")
                
                item.status = "processed"
                item.processed_at = datetime.utcnow()
                item.last_error = None
                processed += 1
            except Exception as e:
                item.retry_count += 1
                item.status = "failed"
                item.last_error = str(e)
                logger.error(f"Error processing inbox item {item.event_id}: {e}")

        db.commit()
        return processed
