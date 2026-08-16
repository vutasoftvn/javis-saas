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
    Application,
    ApplicationSection,
    PolicyProgram,
)
from app.modules.policy_funding.services.proposal_service import ProposalService

router = APIRouter()


class CreateApplicationRequest(BaseModel):
    project_id: int
    program_id: int
    requested_amount: Optional[float] = None
    co_funding_amount: Optional[float] = None


class ApproveSectionRequest(BaseModel):
    section_key: str
    content_approved: str


class SectionResponse(BaseModel):
    id: int
    id_str: str
    application_id: int
    section_key: str
    section_title: str
    sequence_no: int
    content_draft: Optional[str] = None
    content_approved: Optional[str] = None
    is_approved: bool
    missing_fields_jsonb: List[str] = Field(default_factory=list)
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApplicationDetailResponse(BaseModel):
    id: int
    id_str: str
    project_id: int
    program_id: int
    title: str
    status: str
    template_version: str
    requested_amount: Optional[float] = None
    co_funding_amount: Optional[float] = None
    sections: List[SectionResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


def _guard(workspace_id: int, member: WorkspaceMember) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")


@router.post("/applications", response_model=ApplicationDetailResponse, status_code=201)
def create_application(
    payload: CreateApplicationRequest,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Khởi tạo hồ sơ thuyết minh dự án cho một chương trình hỗ trợ.
    """
    _guard(workspace_id, member)
    app_record = ProposalService.initialize_application(
        db=db,
        workspace_id=workspace_id,
        brain_id=member.workspace_id,
        project_id=payload.project_id,
        program_id=payload.program_id,
        requested_amount=payload.requested_amount,
        co_funding_amount=payload.co_funding_amount,
    )
    sections = db.scalars(
        select(ApplicationSection)
        .where(ApplicationSection.application_id == app_record.id)
        .order_by(ApplicationSection.sequence_no.asc())
    ).all()

    return ApplicationDetailResponse(
        id=app_record.id,
        id_str=str(app_record.id),
        project_id=app_record.project_id,
        program_id=app_record.program_id,
        title=app_record.title,
        status=app_record.status,
        template_version=app_record.template_version,
        requested_amount=app_record.requested_amount,
        co_funding_amount=app_record.co_funding_amount,
        sections=[
            SectionResponse(
                id=s.id,
                id_str=str(s.id),
                application_id=s.application_id,
                section_key=s.section_key,
                section_title=s.section_title,
                sequence_no=s.sequence_no,
                content_draft=s.content_draft,
                content_approved=s.content_approved,
                is_approved=s.is_approved,
                missing_fields_jsonb=s.missing_fields_jsonb if isinstance(s.missing_fields_jsonb, list) else [],
                approved_at=s.approved_at,
            )
            for s in sections
        ],
        created_at=app_record.created_at,
        updated_at=app_record.updated_at,
    )


@router.get("/applications/{application_id}", response_model=ApplicationDetailResponse)
def get_application_detail(
    application_id: int,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Xem chi tiết hồ sơ ứng tuyển kèm danh sách các section và trạng thái duyệt.
    """
    _guard(workspace_id, member)
    app_record = db.scalar(
        select(Application).where(
            Application.id == application_id,
            Application.workspace_id == workspace_id,
        )
    )
    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")

    sections = db.scalars(
        select(ApplicationSection)
        .where(ApplicationSection.application_id == app_record.id)
        .order_by(ApplicationSection.sequence_no.asc())
    ).all()

    return ApplicationDetailResponse(
        id=app_record.id,
        id_str=str(app_record.id),
        project_id=app_record.project_id,
        program_id=app_record.program_id,
        title=app_record.title,
        status=app_record.status,
        template_version=app_record.template_version,
        requested_amount=app_record.requested_amount,
        co_funding_amount=app_record.co_funding_amount,
        sections=[
            SectionResponse(
                id=s.id,
                id_str=str(s.id),
                application_id=s.application_id,
                section_key=s.section_key,
                section_title=s.section_title,
                sequence_no=s.sequence_no,
                content_draft=s.content_draft,
                content_approved=s.content_approved,
                is_approved=s.is_approved,
                missing_fields_jsonb=s.missing_fields_jsonb if isinstance(s.missing_fields_jsonb, list) else [],
                approved_at=s.approved_at,
            )
            for s in sections
        ],
        created_at=app_record.created_at,
        updated_at=app_record.updated_at,
    )


@router.post("/applications/{application_id}/generate-section-draft")
def generate_section_draft(
    application_id: int,
    section_key: str = Query(...),
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    AI tự động soạn thảo dự thảo nội dung cho một section cụ thể.
    """
    _guard(workspace_id, member)
    section = ProposalService.generate_section_draft(
        db=db,
        application_id=application_id,
        section_key=section_key,
    )
    return {
        "status": "success",
        "section_key": section.section_key,
        "content_draft": section.content_draft,
        "missing_fields": section.missing_fields_jsonb,
    }


@router.post("/applications/{application_id}/approve-section")
def approve_section(
    application_id: int,
    payload: ApproveSectionRequest,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Founder duyệt và xác nhận nội dung section chính thức.
    """
    _guard(workspace_id, member)
    section = db.scalar(
        select(ApplicationSection).where(
            ApplicationSection.application_id == application_id,
            ApplicationSection.section_key == payload.section_key,
        )
    )
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    section.content_approved = payload.content_approved
    section.is_approved = True
    section.approved_by = member.user_id
    section.approved_at = datetime.utcnow()
    db.commit()

    return {
        "status": "success",
        "section_key": section.section_key,
        "is_approved": True,
        "message": f"Đã duyệt thành công phần {section.section_title}",
    }


@router.post("/applications/{application_id}/export")
def export_application_markdown(
    application_id: int,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Xuất toàn bộ hồ sơ thuyết minh ra định dạng Markdown hoàn chỉnh.
    """
    _guard(workspace_id, member)
    app_record = db.scalar(select(Application).where(Application.id == application_id))
    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")

    sections = db.scalars(
        select(ApplicationSection)
        .where(ApplicationSection.application_id == application_id)
        .order_by(ApplicationSection.sequence_no.asc())
    ).all()

    md_lines = [
        f"# {app_record.title}",
        f"\n**Trạng thái hồ sơ:** {app_record.status} | **Phiên bản biểu mẫu:** {app_record.template_version}",
        f"**Kinh phí đề xuất:** {app_record.requested_amount:,.0f} VND" if app_record.requested_amount else "",
        f"**Vốn đối ứng:** {app_record.co_funding_amount:,.0f} VND" if app_record.co_funding_amount else "",
        "\n---\n",
    ]

    for s in sections:
        content = s.content_approved or s.content_draft or "*(Chưa có nội dung)*"
        md_lines.append(f"## {s.section_title}\n\n{content}\n\n")

    return {
        "title": app_record.title,
        "markdown_content": "\n".join(md_lines),
    }
