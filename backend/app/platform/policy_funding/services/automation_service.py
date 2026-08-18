from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.platform.policy_funding.models import (
    SourceDocument,
    SourceSnapshot,
    AdminPolicyInbox,
    PolicyProgram,
    ProjectProgramMatch,
    MissingRequirement,
)
from app.integrations.channels.models import Outbox


class PolicyAutomationService:
    """
    Dịch vụ xử lý tự động hóa Ingestion từ n8n/crawlers và phát cảnh báo đa kênh (Telegram, Zalo, Email, In-app).
    """

    @classmethod
    def ingest_external_policy_feed(
        cls,
        db: Session,
        workspace_id: int,
        brain_id: int,
        source_title: str,
        source_url: Optional[str],
        authority: Optional[str],
        document_type: str,
        content_raw: str,
        extracted_fields: Optional[Dict[str, Any]] = None,
        confidence: float = 0.85,
    ) -> AdminPolicyInbox:
        """
        Nhận payload từ webhook n8n / crawler, tạo SourceSnapshot và đưa vào Admin Policy Inbox để kiểm duyệt.
        """
        # 1. Tạo Source Document
        doc = SourceDocument(
            workspace_id=workspace_id,
            brain_id=brain_id,
            title=source_title,
            authority=authority or "Nguồn tự động (n8n / Crawler)",
            document_type=document_type,
            source_url=source_url,
            verification_status="UNVERIFIED",
            verification_note="Tự động thu thập từ n8n webhook; đang chờ Admin kiểm tra.",
        )
        db.add(doc)
        db.flush()

        # 2. Tạo Snapshot
        snapshot = SourceSnapshot(
            source_document_id=doc.id,
            content_raw=content_raw,
            extracted_metadata_jsonb=extracted_fields or {},
        )
        db.add(snapshot)

        # 3. Đưa vào Admin Inbox
        inbox_item = AdminPolicyInbox(
            source_title=source_title,
            source_url=source_url,
            detected_at=datetime.utcnow(),
            extracted_summary=f"Phát hiện văn bản mới qua n8n: {source_title}",
            extracted_data_jsonb={
                "source_document_id": doc.id,
                "document_type": document_type,
                "extracted_fields": extracted_fields or {},
            },
            ai_confidence=confidence,
            status="PENDING",
        )
        db.add(inbox_item)
        db.commit()
        db.refresh(inbox_item)
        return inbox_item

    @classmethod
    def dispatch_critical_policy_alert(
        cls,
        db: Session,
        workspace_id: int,
        project_id: int,
        alert_title: str,
        alert_message: str,
        channel: str = "IN_APP",  # IN_APP, TELEGRAM, ZALO, EMAIL
        target_destination: Optional[str] = None,
    ) -> Outbox:
        """
        Gửi cảnh báo khẩn (deadline < 7 ngày, trùng chi phí, chính sách thay đổi) vào hàng đợi Outbox.
        """
        import uuid
        outbox_entry = Outbox(
            workspace_id=workspace_id,
            channel=channel,
            dedupe_key=f"policy_alert_{project_id}_{uuid.uuid4().hex[:12]}",
            payload_jsonb={
                "project_id": project_id,
                "title": f"[CẢNH BÁO NGUỒN LỰC] {alert_title}",
                "message": alert_message,
                "destination": target_destination or "founder_in_app",
                "created_at": datetime.utcnow().isoformat(),
                "urgency": "CRITICAL",
            },
            status="pending",
        )
        db.add(outbox_entry)
        db.commit()
        db.refresh(outbox_entry)
        return outbox_entry
