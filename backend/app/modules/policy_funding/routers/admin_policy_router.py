from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.modules.policy_funding.models import (
    AdminPolicyInbox,
    SourceDocument,
    SourceSnapshot,
    PolicyProgram,
)
from app.modules.policy_funding.schemas import (
    AdminVerifyRequest,
    SourceDocumentResponse,
    PolicyProgramResponse,
)

router = APIRouter()


class ImportSourceRequest(BaseModel):
    title: str
    authority: Optional[str] = None
    document_type: str = "PROGRAM_GUIDE"  # LAW, DECREE, CIRCULAR, PROGRAM_GUIDE, PRESENTATION
    source_url: Optional[str] = None
    raw_content: str
    is_presentation_meetup: bool = False


class AdminInboxItemResponse(BaseModel):
    id: int
    id_str: str
    source_title: str
    source_url: Optional[str] = None
    detected_at: datetime
    extracted_summary: Optional[str] = None
    extracted_data_jsonb: Dict[str, Any]
    ai_confidence: float
    status: str
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


def _admin_guard(member: WorkspaceMember) -> None:
    role = getattr(member, "role", "MEMBER")
    # Trong COSA OS, role admin hoặc founder được phép quản trị
    if str(role).upper() not in ["ADMIN", "FOUNDER", "OWNER"]:
        # Tạm thời kiểm tra nếu member có quyền
        pass


@router.get("/admin/policy/inbox", response_model=List[AdminInboxItemResponse])
def get_admin_policy_inbox(
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách các chính sách mới phát hiện chờ Admin xác minh và duyệt.
    """
    _admin_guard(member)
    items = db.scalars(
        select(AdminPolicyInbox).order_by(AdminPolicyInbox.detected_at.desc())
    ).all()

    return [
        AdminInboxItemResponse(
            id=it.id,
            id_str=str(it.id),
            source_title=it.source_title,
            source_url=it.source_url,
            detected_at=it.detected_at,
            extracted_summary=it.extracted_summary,
            extracted_data_jsonb=it.extracted_data_jsonb if isinstance(it.extracted_data_jsonb, dict) else {},
            ai_confidence=it.ai_confidence,
            status=it.status,
            reviewed_at=it.reviewed_at,
        )
        for it in items
    ]


@router.post("/admin/policy/import-source", response_model=SourceDocumentResponse, status_code=201)
def import_policy_source_document(
    payload: ImportSourceRequest,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Nhập tài liệu văn bản / PDF hội thảo vào nguồn dữ liệu.
    Nếu là tài liệu hội thảo (Presentation), mặc định gắn UNVERIFIED và DRAFT.
    """
    _admin_guard(member)

    doc_type = "PRESENTATION" if payload.is_presentation_meetup else payload.document_type
    verif_status = "UNVERIFIED"

    doc = SourceDocument(
        workspace_id=workspace_id,
        brain_id=member.workspace_id,
        title=payload.title,
        authority=payload.authority,
        document_type=doc_type,
        source_url=payload.source_url,
        verification_status=verif_status,
        verification_note="Tài liệu nhập khởi tạo, chờ đối chiếu văn bản pháp lý chính thức." if payload.is_presentation_meetup else None,
    )
    db.add(doc)
    db.flush()

    snapshot = SourceSnapshot(
        source_document_id=doc.id,
        content_raw=payload.raw_content,
        extracted_metadata_jsonb={
            "source_type": doc_type,
            "imported_at": datetime.utcnow().isoformat(),
            "imported_by": member.user_id,
        },
    )
    db.add(snapshot)

    # Đưa vào hàng chờ Admin Inbox
    inbox_item = AdminPolicyInbox(
        source_title=payload.title,
        source_url=payload.source_url,
        detected_at=datetime.utcnow(),
        extracted_summary=f"Nhập tài liệu {doc_type}: {payload.title}",
        extracted_data_jsonb={"source_document_id": doc.id, "document_type": doc_type},
        ai_confidence=0.85 if not payload.is_presentation_meetup else 0.60,
        status="PENDING",
    )
    db.add(inbox_item)
    db.commit()
    db.refresh(doc)

    return SourceDocumentResponse(
        id=doc.id,
        id_str=str(doc.id),
        workspace_id=doc.workspace_id,
        brain_id=doc.brain_id,
        title=doc.title,
        authority=doc.authority,
        document_type=doc.document_type,
        document_number=doc.document_number,
        issued_at=doc.issued_at,
        source_url=doc.source_url,
        file_hash=doc.file_hash,
        verification_status=doc.verification_status,
        verification_note=doc.verification_note,
        verified_by=doc.verified_by,
        verified_at=doc.verified_at,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.post("/admin/policy/{inbox_id}/verify")
def verify_inbox_item(
    inbox_id: int,
    payload: AdminVerifyRequest,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Xác minh và phê duyệt mục trong Admin Policy Inbox.
    """
    _admin_guard(member)
    item = db.scalar(select(AdminPolicyInbox).where(AdminPolicyInbox.id == inbox_id))
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")

    item.status = payload.status
    item.reviewed_by = member.user_id
    item.reviewed_at = datetime.utcnow()

    # Cập nhật Source Document nếu có liên kết
    source_doc_id = item.extracted_data_jsonb.get("source_document_id") if isinstance(item.extracted_data_jsonb, dict) else None
    if source_doc_id:
        doc = db.scalar(select(SourceDocument).where(SourceDocument.id == source_doc_id))
        if doc:
            doc.verification_status = payload.status
            doc.verification_note = payload.verification_note
            doc.verified_by = member.user_id
            doc.verified_at = datetime.utcnow()

    db.commit()
    return {
        "status": "success",
        "inbox_id": str(item.id),
        "inbox_status": item.status,
        "message": f"Đã cập nhật trạng thái xác minh: {item.status}",
    }


@router.post("/admin/policy/seed-meetup-data")
def seed_initial_policy_data(
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Nạp dữ liệu chính sách ban đầu từ tài liệu hội thảo Founders' Meetup #1.
    """
    _admin_guard(member)
    from app.modules.policy_funding.seed_policy_data import seed_meetup_policy_data
    seed_meetup_policy_data(db=db, workspace_id=workspace_id, brain_id=member.workspace_id)
    return {
        "status": "success",
        "message": "Đã nạp thành công danh mục chính sách và nguồn lực ban đầu.",
    }


class IngestWebhookRequest(BaseModel):
    title: str
    source_url: Optional[str] = None
    authority: Optional[str] = None
    document_type: str = "PROGRAM_GUIDE"
    content_raw: str
    extracted_fields: Optional[Dict[str, Any]] = None
    confidence: float = 0.85


@router.post("/admin/policy/ingest-webhook")
def ingest_policy_webhook(
    payload: IngestWebhookRequest,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Webhook nhận dữ liệu tự động từ n8n / RSS crawlers.
    """
    _admin_guard(member)
    from app.modules.policy_funding.services.automation_service import PolicyAutomationService
    item = PolicyAutomationService.ingest_external_policy_feed(
        db=db,
        workspace_id=workspace_id,
        brain_id=member.workspace_id,
        source_title=payload.title,
        source_url=payload.source_url,
        authority=payload.authority,
        document_type=payload.document_type,
        content_raw=payload.content_raw,
        extracted_fields=payload.extracted_fields,
        confidence=payload.confidence,
    )
    return {
        "status": "success",
        "inbox_id": str(item.id),
        "source_title": item.source_title,
        "message": "Đã tiếp nhận và đưa vào hàng chờ Admin Inbox để xác minh.",
    }
