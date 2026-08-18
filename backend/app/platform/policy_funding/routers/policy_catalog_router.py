from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.platform.policy_funding.models import (
    PolicyProgram,
    PolicyProgramClaim,
    PolicyVerification,
    PolicyChangeProposal,
    ProgramRound,
    EligibilityRule,
    SourceDocument,
)
from app.platform.policy_funding.schemas import (
    PolicyProgramCreate,
    PolicyProgramUpdate,
    PolicyProgramResponse,
    PolicyProgramClaimCreate,
    PolicyProgramClaimUpdate,
    PolicyProgramClaimResponse,
    PolicyVerificationCreate,
    PolicyVerificationResponse,
    PolicyChangeProposalCreate,
    PolicyChangeProposalReview,
    PolicyChangeProposalResponse,
    EligibilityRuleCreate,
    EligibilityRuleResponse,
)
from app.platform.policy_funding.services.matching_service import MatchingService

router = APIRouter()


def _guard(workspace_id: int, member: WorkspaceMember) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")


def _format_program_response(p: PolicyProgram, claims: Optional[List[PolicyProgramClaim]] = None) -> PolicyProgramResponse:
    claims_list = []
    if claims is not None:
        claims_list = [
            PolicyProgramClaimResponse(
                id=c.id,
                id_str=str(c.id),
                program_id=c.program_id,
                claim_type=c.claim_type,
                claim_key=c.claim_key,
                claim_value=c.claim_value,
                source_document_id=c.source_document_id,
                source_page=c.source_page,
                source_excerpt=c.source_excerpt,
                is_verified=c.is_verified,
                verified_value=c.verified_value,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in claims
        ]

    return PolicyProgramResponse(
        id=p.id,
        id_str=str(p.id),
        workspace_id=p.workspace_id,
        brain_id=p.brain_id,
        name=p.name,
        code=p.code,
        summary=p.summary,
        program_type=p.program_type,
        legal_basis=p.legal_basis,
        authority=p.authority,
        geography=p.geography,
        company_types=p.company_types if isinstance(p.company_types, list) else [],
        project_stages=p.project_stages if isinstance(p.project_stages, list) else [],
        trl_min=p.trl_min,
        industries=p.industries if isinstance(p.industries, list) else [],
        funding_min=p.funding_min,
        funding_max=p.funding_max,
        currency=p.currency,
        matching_fund_pct=p.matching_fund_pct,
        eligible_costs=p.eligible_costs if isinstance(p.eligible_costs, list) else [],
        status=p.status,
        verification_status=p.verification_status or "PENDING_FOUNDER_VERIFICATION",
        matching_mode=p.matching_mode or "soft",
        publish_to_matching=p.publish_to_matching,
        source_claim=p.source_claim,
        claimed_values_jsonb=p.claimed_values_jsonb if isinstance(p.claimed_values_jsonb, dict) else {},
        source_document_id=p.source_document_id,
        source_url=p.source_url,
        application_window_start=p.application_window_start,
        application_window_end=p.application_window_end,
        last_verified_at=p.last_verified_at,
        claims=claims_list,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.get("/policy-programs", response_model=List[PolicyProgramResponse])
def list_policy_programs(
    workspace_id: int = Query(...),
    status: Optional[str] = Query(None),
    verification_status: Optional[str] = Query(None),
    program_type: Optional[str] = Query(None),
    geography: Optional[str] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách các chương trình chính sách trong catalog theo các tiêu chí lọc.
    """
    _guard(workspace_id, member)

    query = select(PolicyProgram).where(PolicyProgram.workspace_id == workspace_id)
    if status:
        query = query.where(PolicyProgram.status == status)
    if verification_status:
        query = query.where(PolicyProgram.verification_status == verification_status)
    if program_type:
        query = query.where(PolicyProgram.program_type == program_type)
    if geography:
        query = query.where(PolicyProgram.geography == geography)

    programs = db.scalars(query.order_by(PolicyProgram.created_at.desc())).all()
    return [_format_program_response(p) for p in programs]


@router.get("/policy-programs/current-benefits", response_model=List[PolicyProgramResponse])
def get_current_benefits(
    workspace_id: int = Query(...),
    program_type: Optional[str] = Query(None),
    geography: Optional[str] = Query(None),
    verification_status: Optional[str] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Lấy danh mục Quyền lợi hiện hành (Current Benefits):
    Chỉ lấy các chương trình có publish_to_matching = True và không thuộc DRAFT_WATCHLIST.
    """
    _guard(workspace_id, member)

    query = select(PolicyProgram).where(
        PolicyProgram.workspace_id == workspace_id,
        PolicyProgram.publish_to_matching == True,
        PolicyProgram.verification_status != "DRAFT_WATCHLIST",
        PolicyProgram.status.notin_(["CLOSED", "REJECTED_SOURCE_DATA"]),
    )
    if verification_status:
        query = query.where(PolicyProgram.verification_status == verification_status)
    if program_type:
        query = query.where(PolicyProgram.program_type == program_type)
    if geography:
        query = query.where(PolicyProgram.geography == geography)

    programs = db.scalars(query.order_by(PolicyProgram.created_at.asc())).all()
    
    # Load claims for each program
    results = []
    for p in programs:
        claims = db.scalars(select(PolicyProgramClaim).where(PolicyProgramClaim.program_id == p.id)).all()
        results.append(_format_program_response(p, claims))

    return results


@router.get("/policy-programs/draft-watchlist", response_model=List[PolicyProgramResponse])
def get_draft_watchlist(
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Lấy danh mục các chương trình dự thảo đang theo dõi (Draft Watchlist).
    """
    _guard(workspace_id, member)

    query = select(PolicyProgram).where(
        PolicyProgram.workspace_id == workspace_id,
        PolicyProgram.verification_status == "DRAFT_WATCHLIST",
    )
    programs = db.scalars(query.order_by(PolicyProgram.created_at.asc())).all()
    return [_format_program_response(p) for p in programs]


@router.get("/policy-programs/{program_id}", response_model=PolicyProgramResponse)
def get_policy_program_detail(
    program_id: int,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Xem chi tiết 1 chương trình chính sách cụ thể và danh sách claims của nó.
    """
    _guard(workspace_id, member)
    p = db.scalar(
        select(PolicyProgram).where(
            PolicyProgram.id == program_id,
            PolicyProgram.workspace_id == workspace_id,
        )
    )
    if not p:
        raise HTTPException(status_code=404, detail="Policy program not found")

    claims = db.scalars(select(PolicyProgramClaim).where(PolicyProgramClaim.program_id == p.id)).all()
    return _format_program_response(p, claims)


@router.post("/policy-programs/{program_id}/verify", response_model=PolicyVerificationResponse)
def verify_policy_program(
    program_id: int,
    payload: PolicyVerificationCreate,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Quy trình kiểm chứng quyền lợi dành cho Founder/Admin:
    - Cập nhật trạng thái kiểm chứng (VERIFIED_ACTIVE, VERIFIED_ENACTED, REJECTED_SOURCE_DATA...)
    - Gắn URL hoặc văn bản pháp lý chính thức
    - Cập nhật các claim đã được xác minh
    - Lưu nhật ký kiểm chứng vào PolicyVerification
    - Tự động tính toán lại Matching Score cho các Project liên quan
    """
    _guard(workspace_id, member)

    program = db.scalar(
        select(PolicyProgram).where(
            PolicyProgram.id == program_id,
            PolicyProgram.workspace_id == workspace_id,
        )
    )
    if not program:
        raise HTTPException(status_code=404, detail="Policy program not found")

    # 1. Update program verification fields
    program.verification_status = payload.result_status
    program.last_verified_at = datetime.utcnow()
    if payload.official_source_url:
        program.source_url = payload.official_source_url
    if payload.official_authority:
        program.authority = payload.official_authority

    if payload.result_status in ["REJECTED_SOURCE_DATA", "VERIFIED_CLOSED"]:
        program.publish_to_matching = False
    elif payload.result_status in ["VERIFIED_ACTIVE", "VERIFIED_ENACTED"]:
        program.publish_to_matching = True

    # 2. Update claims if specified
    if payload.updated_claims:
        for claim_id_str, verified_val in payload.updated_claims.items():
            try:
                c_id = int(claim_id_str)
                claim = db.scalar(
                    select(PolicyProgramClaim).where(
                        PolicyProgramClaim.id == c_id,
                        PolicyProgramClaim.program_id == program_id,
                    )
                )
                if claim:
                    claim.is_verified = True
                    claim.verified_value = verified_val
            except ValueError:
                continue

    # 3. Create verification log
    verification = PolicyVerification(
        program_id=program_id,
        verified_by=member.user_id,
        verified_at=datetime.utcnow(),
        official_source_url=payload.official_source_url,
        official_document_id=payload.official_document_id,
        official_authority=payload.official_authority,
        result_status=payload.result_status,
        notes=payload.notes,
        diff_jsonb=payload.diff_jsonb,
    )
    db.add(verification)
    db.commit()
    db.refresh(verification)

    # 4. Trigger Recalculate matches for affected projects
    MatchingService.recalculate_program_matches(db=db, program_id=program_id)

    return PolicyVerificationResponse(
        id=verification.id,
        id_str=str(verification.id),
        program_id=verification.program_id,
        verified_by=verification.verified_by,
        verified_at=verification.verified_at,
        official_source_url=verification.official_source_url,
        official_authority=verification.official_authority,
        result_status=verification.result_status,
        notes=verification.notes,
        diff_jsonb=verification.diff_jsonb if isinstance(verification.diff_jsonb, dict) else {},
        created_at=verification.created_at,
    )


@router.get("/policy-programs/{program_id}/claims", response_model=List[PolicyProgramClaimResponse])
def list_program_claims(
    program_id: int,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách các Claims của một chương trình.
    """
    _guard(workspace_id, member)
    claims = db.scalars(
        select(PolicyProgramClaim)
        .join(PolicyProgram, PolicyProgramClaim.program_id == PolicyProgram.id)
        .where(
            PolicyProgramClaim.program_id == program_id,
            PolicyProgram.workspace_id == workspace_id,
        )
    ).all()

    return [
        PolicyProgramClaimResponse(
            id=c.id,
            id_str=str(c.id),
            program_id=c.program_id,
            claim_type=c.claim_type,
            claim_key=c.claim_key,
            claim_value=c.claim_value,
            source_document_id=c.source_document_id,
            source_page=c.source_page,
            source_excerpt=c.source_excerpt,
            is_verified=c.is_verified,
            verified_value=c.verified_value,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in claims
    ]


@router.post("/policy-programs/{program_id}/claims", response_model=PolicyProgramClaimResponse, status_code=201)
def create_program_claim(
    program_id: int,
    payload: PolicyProgramClaimCreate,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Thêm một claim mới cho chương trình.
    """
    _guard(workspace_id, member)
    program = db.scalar(
        select(PolicyProgram).where(
            PolicyProgram.id == program_id,
            PolicyProgram.workspace_id == workspace_id,
        )
    )
    if not program:
        raise HTTPException(status_code=404, detail="Policy program not found")

    claim = PolicyProgramClaim(
        program_id=program_id,
        claim_type=payload.claim_type,
        claim_key=payload.claim_key,
        claim_value=payload.claim_value,
        source_document_id=payload.source_document_id,
        source_page=payload.source_page,
        source_excerpt=payload.source_excerpt,
        is_verified=payload.is_verified,
        verified_value=payload.verified_value,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)

    return PolicyProgramClaimResponse(
        id=claim.id,
        id_str=str(claim.id),
        program_id=claim.program_id,
        claim_type=claim.claim_type,
        claim_key=claim.claim_key,
        claim_value=claim.claim_value,
        source_document_id=claim.source_document_id,
        source_page=claim.source_page,
        source_excerpt=claim.source_excerpt,
        is_verified=claim.is_verified,
        verified_value=claim.verified_value,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
    )


@router.put("/policy-programs/{program_id}/claims/{claim_id}", response_model=PolicyProgramClaimResponse)
def update_program_claim(
    program_id: int,
    claim_id: int,
    payload: PolicyProgramClaimUpdate,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Cập nhật một claim (sửa nội dung hoặc xác minh).
    """
    _guard(workspace_id, member)
    claim = db.scalar(
        select(PolicyProgramClaim)
        .join(PolicyProgram, PolicyProgramClaim.program_id == PolicyProgram.id)
        .where(
            PolicyProgramClaim.id == claim_id,
            PolicyProgramClaim.program_id == program_id,
            PolicyProgram.workspace_id == workspace_id,
        )
    )
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    if payload.claim_value is not None:
        claim.claim_value = payload.claim_value
    if payload.is_verified is not None:
        claim.is_verified = payload.is_verified
    if payload.verified_value is not None:
        claim.verified_value = payload.verified_value

    db.commit()
    db.refresh(claim)

    return PolicyProgramClaimResponse(
        id=claim.id,
        id_str=str(claim.id),
        program_id=claim.program_id,
        claim_type=claim.claim_type,
        claim_key=claim.claim_key,
        claim_value=claim.claim_value,
        source_document_id=claim.source_document_id,
        source_page=claim.source_page,
        source_excerpt=claim.source_excerpt,
        is_verified=claim.is_verified,
        verified_value=claim.verified_value,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
    )


@router.get("/policy-change-proposals", response_model=List[PolicyChangeProposalResponse])
def list_change_proposals(
    workspace_id: int = Query(...),
    program_id: Optional[int] = Query(None),
    review_status: Optional[str] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách các đề xuất thay đổi chính sách phát hiện bởi AI hoặc đề xuất bởi Founder.
    """
    _guard(workspace_id, member)

    query = select(PolicyChangeProposal)
    if program_id:
        query = query.where(PolicyChangeProposal.program_id == program_id)
    if review_status:
        query = query.where(PolicyChangeProposal.review_status == review_status)

    proposals = db.scalars(query.order_by(PolicyChangeProposal.detected_at.desc())).all()

    return [
        PolicyChangeProposalResponse(
            id=p.id,
            id_str=str(p.id),
            program_id=p.program_id,
            change_type=p.change_type,
            field_name=p.field_name,
            old_value=p.old_value,
            new_value=p.new_value,
            source_url=p.source_url,
            source_excerpt=p.source_excerpt,
            confidence=p.confidence,
            ai_model=p.ai_model,
            review_status=p.review_status,
            reviewed_by=p.reviewed_by,
            reviewed_at=p.reviewed_at,
            review_notes=p.review_notes,
            detected_at=p.detected_at,
            created_at=p.created_at,
        )
        for p in proposals
    ]


@router.post("/policy-change-proposals", response_model=PolicyChangeProposalResponse, status_code=201)
def create_change_proposal(
    payload: PolicyChangeProposalCreate,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Tạo một đề xuất thay đổi chính sách (AI Agent hoặc Founder).
    """
    _guard(workspace_id, member)

    proposal = PolicyChangeProposal(
        program_id=payload.program_id,
        change_type=payload.change_type,
        field_name=payload.field_name,
        old_value=payload.old_value,
        new_value=payload.new_value,
        source_url=payload.source_url,
        source_excerpt=payload.source_excerpt,
        confidence=payload.confidence,
        ai_model=payload.ai_model,
        review_status="PENDING",
        detected_at=datetime.utcnow(),
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    return PolicyChangeProposalResponse(
        id=proposal.id,
        id_str=str(proposal.id),
        program_id=proposal.program_id,
        change_type=proposal.change_type,
        field_name=proposal.field_name,
        old_value=proposal.old_value,
        new_value=proposal.new_value,
        source_url=proposal.source_url,
        source_excerpt=proposal.source_excerpt,
        confidence=proposal.confidence,
        ai_model=proposal.ai_model,
        review_status=proposal.review_status,
        reviewed_by=proposal.reviewed_by,
        reviewed_at=proposal.reviewed_at,
        review_notes=proposal.review_notes,
        detected_at=proposal.detected_at,
        created_at=proposal.created_at,
    )


@router.post("/policy-change-proposals/{proposal_id}/review", response_model=PolicyChangeProposalResponse)
def review_change_proposal(
    proposal_id: int,
    payload: PolicyChangeProposalReview,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Duyệt hoặc từ chối một đề xuất thay đổi chính sách.
    Nếu APPROVED: Cập nhật giá trị vào PolicyProgram tương ứng và tính toán lại match.
    """
    _guard(workspace_id, member)

    proposal = db.scalar(select(PolicyChangeProposal).where(PolicyChangeProposal.id == proposal_id))
    if not proposal:
        raise HTTPException(status_code=404, detail="Change proposal not found")

    proposal.review_status = payload.review_status
    proposal.reviewed_by = member.user_id
    proposal.reviewed_at = datetime.utcnow()
    proposal.review_notes = payload.review_notes

    if payload.review_status == "APPROVED" and proposal.program_id and proposal.field_name:
        program = db.scalar(select(PolicyProgram).where(PolicyProgram.id == proposal.program_id))
        if program and hasattr(program, proposal.field_name):
            try:
                # Cập nhật giá trị trường
                setattr(program, proposal.field_name, proposal.new_value)
                program.last_verified_at = datetime.utcnow()
            except Exception:
                pass

    db.commit()
    db.refresh(proposal)

    if payload.review_status == "APPROVED" and proposal.program_id:
        MatchingService.recalculate_program_matches(db=db, program_id=proposal.program_id)

    return PolicyChangeProposalResponse(
        id=proposal.id,
        id_str=str(proposal.id),
        program_id=proposal.program_id,
        change_type=proposal.change_type,
        field_name=proposal.field_name,
        old_value=proposal.old_value,
        new_value=proposal.new_value,
        source_url=proposal.source_url,
        source_excerpt=proposal.source_excerpt,
        confidence=proposal.confidence,
        ai_model=proposal.ai_model,
        review_status=proposal.review_status,
        reviewed_by=proposal.reviewed_by,
        reviewed_at=proposal.reviewed_at,
        review_notes=proposal.review_notes,
        detected_at=proposal.detected_at,
        created_at=proposal.created_at,
    )

