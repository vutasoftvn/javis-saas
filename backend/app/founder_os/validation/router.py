from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.platform.auth.models import WorkspaceMember
from app.platform.vault.models import Brain
from app.founder_os.validation.service import ValidationEngineService
from app.founder_os.validation.models import (
    StructuredClaim,
    FieldRevision,
    ValidationAssumption,
    ValidationHypothesis,
    ValidationExperiment,
    ValidationEvidence,
    ValidationReview,
    ValidationDecision,
)
from app.founder_os.validation.schemas import (
    ValidationSessionStartRequest,
    ValidationSessionResponse,
    StructuredClaimCreate,
    StructuredClaimConfirmRequest,
    StructuredClaimEditRequest,
    StructuredClaimResponse,
    FieldRevisionResponse,
    AssumptionCreate,
    AssumptionUpdate,
    AssumptionResponse,
    HypothesisCreate,
    HypothesisResponse,
    ExperimentCreate,
    ExperimentResponse,
    EvidenceCreate,
    EvidenceResponse,
    ValidationReviewCreate,
    ValidationReviewResponse,
    ValidationDecisionCreate,
    ValidationDecisionResponse,
    StateVectorResponse,
    ValidationChatRequest,
    ValidationChatResponse,
    RiskMatrixResponse,
    GeneratedHypothesisResponse,
    RecommendedExperimentResponse,
    NextBestActionDetailResponse,
    ReviewPackageResponse,
)
from app.founder_os.validation.interview_service import ValidationInterviewService

from app.founder_os.validation.risk_service import RiskPrioritizationService
from app.founder_os.validation.review_service import ValidationReviewService

router = APIRouter(tags=["Project Validation Engine"])


def _resolve_brain_id(db: Session, workspace_id: int) -> int:
    brain = db.scalars(
        select(Brain).where(Brain.workspace_id == workspace_id)
    ).first()
    return brain.id if brain else workspace_id


# -------------------------------------------------------------------------
# SESSIONS & ADAPTIVE INTERVIEW CHAT
# -------------------------------------------------------------------------

@router.post("/projects/{project_id}/validation/session/start", response_model=ValidationSessionResponse)
def start_validation_session(
    project_id: int,
    body: ValidationSessionStartRequest,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    brain_id = _resolve_brain_id(db, member.workspace_id)
    session = ValidationEngineService.get_or_create_session(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=brain_id,
        project_id=project_id,
        initial_topic=body.initial_topic.value if body.initial_topic else "CUSTOMER",
    )
    return session


@router.post("/projects/{project_id}/validation/chat", response_model=ValidationChatResponse)
async def chat_validation_interview(
    project_id: int,
    body: ValidationChatRequest,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    brain_id = _resolve_brain_id(db, member.workspace_id)
    res = await ValidationInterviewService.process_user_turn(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=brain_id,
        project_id=project_id,
        user_message=body.message,
        current_topic=body.current_topic,
    )
    return res


@router.get("/projects/{project_id}/validation/session", response_model=ValidationSessionResponse)
def get_validation_session(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    brain_id = _resolve_brain_id(db, member.workspace_id)
    session = ValidationEngineService.get_or_create_session(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=brain_id,
        project_id=project_id,
    )
    return session


# -------------------------------------------------------------------------
# STRUCTURED CLAIMS & REVISIONS
# -------------------------------------------------------------------------

@router.get("/projects/{project_id}/validation/claims", response_model=List[StructuredClaimResponse])
def list_claims(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    claims = db.scalars(
        select(StructuredClaim)
        .where(
            StructuredClaim.workspace_id == member.workspace_id,
            StructuredClaim.project_id == project_id,
        )
        .order_by(desc(StructuredClaim.created_at))
    ).all()
    return claims


@router.post("/projects/{project_id}/validation/claims", response_model=StructuredClaimResponse)
def create_claim(
    project_id: int,
    body: StructuredClaimCreate,
    session_id: Optional[int] = None,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    brain_id = _resolve_brain_id(db, member.workspace_id)
    claim = ValidationEngineService.create_claim(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=brain_id,
        project_id=project_id,
        claim_in=body,
        session_id=session_id,
    )
    return claim


@router.post("/projects/{project_id}/validation/claims/{claim_id}/confirm", response_model=StructuredClaimResponse)
def confirm_claim(
    project_id: int,
    claim_id: int,
    body: StructuredClaimConfirmRequest,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    try:
        return ValidationEngineService.confirm_claim(
            db=db,
            claim_id=claim_id,
            confidence=body.confidence or 1.0,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/projects/{project_id}/validation/claims/{claim_id}/edit", response_model=StructuredClaimResponse)
def edit_claim(
    project_id: int,
    claim_id: int,
    body: StructuredClaimEditRequest,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    try:
        return ValidationEngineService.edit_claim(
            db=db,
            claim_id=claim_id,
            edit_in=body,
            changed_by="FOUNDER",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/projects/{project_id}/validation/revisions", response_model=List[FieldRevisionResponse])
def list_field_revisions(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    revisions = db.scalars(
        select(FieldRevision)
        .where(
            FieldRevision.workspace_id == member.workspace_id,
            FieldRevision.project_id == project_id,
        )
        .order_by(desc(FieldRevision.created_at))
    ).all()
    return revisions


# -------------------------------------------------------------------------
# ASSUMPTIONS
# -------------------------------------------------------------------------

@router.get("/projects/{project_id}/validation/assumptions", response_model=List[AssumptionResponse])
def list_assumptions(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    assumptions = db.scalars(
        select(ValidationAssumption)
        .where(
            ValidationAssumption.workspace_id == member.workspace_id,
            ValidationAssumption.project_id == project_id,
        )
        .order_by(desc(ValidationAssumption.risk_score))
    ).all()
    return assumptions


@router.post("/projects/{project_id}/validation/assumptions", response_model=AssumptionResponse)
def create_assumption(
    project_id: int,
    body: AssumptionCreate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    brain_id = _resolve_brain_id(db, member.workspace_id)
    return ValidationEngineService.create_assumption(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=brain_id,
        project_id=project_id,
        assumption_in=body,
    )


@router.put("/projects/{project_id}/validation/assumptions/{assumption_id}", response_model=AssumptionResponse)
def update_assumption(
    project_id: int,
    assumption_id: int,
    body: AssumptionUpdate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    try:
        return ValidationEngineService.update_assumption(
            db=db,
            assumption_id=assumption_id,
            update_in=body,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# -------------------------------------------------------------------------
# HYPOTHESES & EXPERIMENTS
# -------------------------------------------------------------------------

@router.post("/projects/{project_id}/validation/hypotheses", response_model=HypothesisResponse)
def create_hypothesis(
    project_id: int,
    body: HypothesisCreate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    brain_id = _resolve_brain_id(db, member.workspace_id)
    return ValidationEngineService.build_hypothesis(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=brain_id,
        project_id=project_id,
        hypo_in=body,
    )


@router.post("/projects/{project_id}/validation/experiments", response_model=ExperimentResponse)
def create_experiment(
    project_id: int,
    body: ExperimentCreate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    brain_id = _resolve_brain_id(db, member.workspace_id)
    return ValidationEngineService.create_experiment(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=brain_id,
        project_id=project_id,
        exp_in=body,
    )


@router.post("/projects/{project_id}/validation/evidence", response_model=EvidenceResponse)
def record_evidence(
    project_id: int,
    body: EvidenceCreate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    brain_id = _resolve_brain_id(db, member.workspace_id)
    return ValidationEngineService.record_evidence(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=brain_id,
        project_id=project_id,
        evi_in=body,
    )


# -------------------------------------------------------------------------
# REVIEWS & DECISIONS
# -------------------------------------------------------------------------

@router.post("/projects/{project_id}/validation/reviews", response_model=ValidationReviewResponse)
def create_review(
    project_id: int,
    body: ValidationReviewCreate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    brain_id = _resolve_brain_id(db, member.workspace_id)
    return ValidationEngineService.create_review(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=brain_id,
        project_id=project_id,
        review_in=body,
    )


@router.post("/projects/{project_id}/validation/decisions", response_model=ValidationDecisionResponse)
def record_decision(
    project_id: int,
    body: ValidationDecisionCreate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    brain_id = _resolve_brain_id(db, member.workspace_id)
    return ValidationEngineService.record_decision(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=brain_id,
        project_id=project_id,
        decision_in=body,
        user_id=member.user_id,
    )


# -------------------------------------------------------------------------
# STATE VECTOR
# -------------------------------------------------------------------------

@router.get("/projects/{project_id}/validation/state-vector", response_model=StateVectorResponse)
def get_state_vector(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return ValidationEngineService.get_state_vector(db=db, project_id=project_id)


# -------------------------------------------------------------------------
# PHASE 3: RISK MATRIX & EXPERIMENT ENGINE
# -------------------------------------------------------------------------

@router.get("/projects/{project_id}/validation/risk-matrix", response_model=RiskMatrixResponse)
def get_risk_matrix(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return RiskPrioritizationService.get_risk_matrix(
        db=db,
        workspace_id=member.workspace_id,
        project_id=project_id,
    )


@router.get("/projects/{project_id}/validation/assumptions/riskiest", response_model=List[AssumptionResponse])
def get_riskiest_assumptions(
    project_id: int,
    limit: int = 5,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return RiskPrioritizationService.get_riskiest_assumptions(
        db=db,
        workspace_id=member.workspace_id,
        project_id=project_id,
        limit=limit,
    )


@router.post("/projects/{project_id}/validation/assumptions/{assumption_id}/generate-hypothesis", response_model=GeneratedHypothesisResponse)
async def generate_hypothesis_from_assumption(
    project_id: int,
    assumption_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    brain_id = _resolve_brain_id(db, member.workspace_id)
    try:
        return await RiskPrioritizationService.generate_hypothesis_from_assumption(
            db=db,
            workspace_id=member.workspace_id,
            brain_id=brain_id,
            project_id=project_id,
            assumption_id=assumption_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/projects/{project_id}/validation/hypotheses/{hypothesis_id}/recommend-experiment", response_model=RecommendedExperimentResponse)
async def recommend_experiment_for_hypothesis(
    project_id: int,
    hypothesis_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    brain_id = _resolve_brain_id(db, member.workspace_id)
    try:
        return await RiskPrioritizationService.recommend_experiment_for_hypothesis(
            db=db,
            workspace_id=member.workspace_id,
            brain_id=brain_id,
            project_id=project_id,
            hypothesis_id=hypothesis_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/projects/{project_id}/validation/hypotheses", response_model=List[HypothesisResponse])
def list_hypotheses(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return db.scalars(
        select(ValidationHypothesis)
        .where(
            ValidationHypothesis.workspace_id == member.workspace_id,
            ValidationHypothesis.project_id == project_id,
        )
        .order_by(desc(ValidationHypothesis.created_at))
    ).all()


@router.get("/projects/{project_id}/validation/experiments", response_model=List[ExperimentResponse])
def list_experiments(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return db.scalars(
        select(ValidationExperiment)
        .where(
            ValidationExperiment.workspace_id == member.workspace_id,
            ValidationExperiment.project_id == project_id,
        )
        .order_by(desc(ValidationExperiment.created_at))
    ).all()


@router.get("/projects/{project_id}/validation/evidence", response_model=List[EvidenceResponse])
def list_evidence(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return db.scalars(
        select(ValidationEvidence)
        .where(
            ValidationEvidence.workspace_id == member.workspace_id,
            ValidationEvidence.project_id == project_id,
        )
        .order_by(desc(ValidationEvidence.created_at))
    ).all()


# -------------------------------------------------------------------------
# PHASE 4: AI REVIEWER & SINGLE NEXT BEST ACTION
# -------------------------------------------------------------------------

@router.post("/projects/{project_id}/validation/hypotheses/{hypothesis_id}/review/ai", response_model=ValidationReviewResponse)
async def perform_ai_review(
    project_id: int,
    hypothesis_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    brain_id = _resolve_brain_id(db, member.workspace_id)
    try:
        return await ValidationReviewService.perform_ai_review(
            db=db,
            workspace_id=member.workspace_id,
            brain_id=brain_id,
            project_id=project_id,
            hypothesis_id=hypothesis_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/projects/{project_id}/validation/next-best-action", response_model=NextBestActionDetailResponse)
def get_single_next_best_action(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return ValidationReviewService.synthesize_single_next_best_action(
        db=db,
        workspace_id=member.workspace_id,
        project_id=project_id,
    )


@router.get("/projects/{project_id}/validation/reviews/latest", response_model=Optional[ValidationReviewResponse])
def get_latest_review(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return db.scalars(
        select(ValidationReview)
        .where(
            ValidationReview.workspace_id == member.workspace_id,
            ValidationReview.project_id == project_id,
        )
        .order_by(desc(ValidationReview.created_at))
    ).first()


@router.get("/projects/{project_id}/validation/hypotheses/{hypothesis_id}/review-package", response_model=ReviewPackageResponse)
def export_review_package(
    project_id: int,
    hypothesis_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    try:
        return ValidationReviewService.export_review_package(
            db=db,
            workspace_id=member.workspace_id,
            project_id=project_id,
            hypothesis_id=hypothesis_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# -------------------------------------------------------------------------
# F2 & F3: CUSTOMER DISCOVERY, AUDIT & SCORECARD ENDPOINTS
# -------------------------------------------------------------------------

from app.founder_os.validation.question_auditor_service import QuestionAuditorService
from app.founder_os.validation.customer_discovery_service import CustomerDiscoveryService
from app.founder_os.validation.problem_intelligence_service import ProblemIntelligenceService
from app.founder_os.validation.schemas import (
    QuestionAuditRequest,
    QuestionAuditResponse,
    InterviewScriptGenerateRequest,
    InterviewScriptResponse,
    CustomerContactCreate,
    CustomerContactResponse,
    InterviewSessionCreate,
    InterviewSessionResponse,
    VerbatimQuoteCreate,
    VerbatimQuoteResponse,
    ProblemScorecardRequest,
    ProblemScorecardResponse,
    DataAutopsyResponse,
    RoleCoverageResponse,
    SolutionBiasRiskResponse,
)


@router.post("/projects/{project_id}/validation/audit-question", response_model=QuestionAuditResponse)
async def audit_interview_question(
    project_id: int,
    body: QuestionAuditRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return await QuestionAuditorService.audit_question(
        question=body.question,
        research_objective=body.research_objective or "",
    )


@router.post("/projects/{project_id}/validation/interview-script", response_model=InterviewScriptResponse)
async def generate_interview_script(
    project_id: int,
    body: InterviewScriptGenerateRequest,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    from app.founder_os.strategy.models import Project
    project = db.scalar(select(Project).where(Project.id == project_id))
    project_context = f"Project: {project.name if project else 'SaaS'}. Focus: {body.focus_topic or 'Core Problem'}"
    return await CustomerDiscoveryService.generate_interview_script(
        project_context=project_context,
        target_segment=body.target_segment or "Target Customer",
    )


@router.post("/projects/{project_id}/validation/contacts", response_model=CustomerContactResponse)
def create_customer_contact(
    project_id: int,
    body: CustomerContactCreate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    contact = CustomerDiscoveryService.create_contact(
        db=db, workspace_id=member.workspace_id, project_id=project_id, data=body
    )
    return CustomerContactResponse(
        id=contact.id,
        project_id=contact.project_id,
        name=contact.name,
        role=contact.role,
        segment=contact.segment,
        company=contact.company,
        contact_info=contact.contact_info,
        notes=contact.notes,
        created_at=contact.created_at,
    )


@router.get("/projects/{project_id}/validation/contacts", response_model=List[CustomerContactResponse])
def list_customer_contacts(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    contacts = CustomerDiscoveryService.list_contacts(
        db=db, workspace_id=member.workspace_id, project_id=project_id
    )
    return [
        CustomerContactResponse(
            id=c.id,
            project_id=c.project_id,
            name=c.name,
            role=c.role,
            segment=c.segment,
            company=c.company,
            contact_info=c.contact_info,
            notes=c.notes,
            created_at=c.created_at,
        )
        for c in contacts
    ]


@router.post("/projects/{project_id}/validation/interviews", response_model=InterviewSessionResponse)
def create_interview_session(
    project_id: int,
    body: InterviewSessionCreate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    session = CustomerDiscoveryService.create_interview_session(
        db=db, workspace_id=member.workspace_id, project_id=project_id, data=body
    )
    return InterviewSessionResponse(
        id=session.id,
        project_id=session.project_id,
        contact_id=session.contact_id,
        role=session.role,
        segment=session.segment,
        interview_date=session.interview_date,
        duration_minutes=session.duration_minutes,
        raw_notes=session.raw_notes,
        transcript=session.transcript,
        session_summary=session.session_summary,
        referral_notes=session.referral_notes,
        quotes_count=0,
        created_at=session.created_at,
    )


@router.get("/projects/{project_id}/validation/interviews", response_model=List[InterviewSessionResponse])
def list_interview_sessions(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    sessions = CustomerDiscoveryService.list_interview_sessions(
        db=db, workspace_id=member.workspace_id, project_id=project_id
    )
    return [InterviewSessionResponse(**s) for s in sessions]


@router.post("/projects/{project_id}/validation/interviews/{session_id}/quotes", response_model=VerbatimQuoteResponse)
def add_verbatim_quote(
    project_id: int,
    session_id: int,
    body: VerbatimQuoteCreate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    quote = CustomerDiscoveryService.add_verbatim_quote(
        db=db,
        workspace_id=member.workspace_id,
        project_id=project_id,
        session_id=session_id,
        data=body,
    )
    return VerbatimQuoteResponse(
        id=quote.id,
        project_id=quote.project_id,
        session_id=quote.session_id,
        raw_quote=quote.raw_quote,
        interpretation=quote.interpretation,
        interpretation_actor=quote.interpretation_actor,
        tags=quote.tags_jsonb or [],
        buying_signal_level=quote.buying_signal_level,
        linked_assumption_id=quote.linked_assumption_id,
        created_at=quote.created_at,
    )


@router.post("/projects/{project_id}/validation/interviews/{session_id}/extract-quotes")
async def extract_quotes_from_session(
    project_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    try:
        return await CustomerDiscoveryService.analyze_and_extract_quotes(
            db=db,
            workspace_id=member.workspace_id,
            project_id=project_id,
            session_id=session_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/projects/{project_id}/validation/quotes", response_model=List[VerbatimQuoteResponse])
def list_quotes(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    quotes = CustomerDiscoveryService.list_quotes_by_project(
        db=db, workspace_id=member.workspace_id, project_id=project_id
    )
    return [
        VerbatimQuoteResponse(
            id=q.id,
            project_id=q.project_id,
            session_id=q.session_id,
            raw_quote=q.raw_quote,
            interpretation=q.interpretation,
            interpretation_actor=q.interpretation_actor,
            tags=q.tags_jsonb or [],
            buying_signal_level=q.buying_signal_level,
            linked_assumption_id=q.linked_assumption_id,
            created_at=q.created_at,
        )
        for q in quotes
    ]


@router.get("/projects/{project_id}/validation/problem-scorecard", response_model=ProblemScorecardResponse)
def get_problem_scorecard(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return ProblemIntelligenceService.get_or_calculate_scorecard(
        db=db, workspace_id=member.workspace_id, project_id=project_id
    )


@router.post("/projects/{project_id}/validation/problem-scorecard", response_model=ProblemScorecardResponse)
def update_problem_scorecard(
    project_id: int,
    body: ProblemScorecardRequest,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return ProblemIntelligenceService.get_or_calculate_scorecard(
        db=db, workspace_id=member.workspace_id, project_id=project_id, override_data=body
    )


@router.get("/projects/{project_id}/validation/role-coverage", response_model=RoleCoverageResponse)
def get_role_coverage(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return ProblemIntelligenceService.evaluate_role_coverage(
        db=db, workspace_id=member.workspace_id, project_id=project_id
    )


@router.post("/projects/{project_id}/validation/autopsy", response_model=DataAutopsyResponse)
async def run_data_autopsy(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return await ProblemIntelligenceService.run_data_autopsy(
        db=db, workspace_id=member.workspace_id, project_id=project_id
    )


@router.get("/projects/{project_id}/validation/solution-bias", response_model=SolutionBiasRiskResponse)
def get_solution_bias_risk(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    res = RiskPrioritizationService.detect_solution_bias_risk(
        db=db, workspace_id=member.workspace_id, project_id=project_id
    )
    return SolutionBiasRiskResponse(**res)




