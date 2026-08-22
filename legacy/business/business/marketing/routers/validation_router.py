from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from core.auth import get_current_workspace_member
from db.session import get_db
from db.models import Brain, WorkspaceMember
from business.marketing.models import MarketingExperiment, MarketingLearning, MarketingDecision
from business.marketing.models_validation import (
    Assumption,
    Evidence,
    KnowledgeStatement,
    CanvasRevision,
    CustomerInterview,
    MarketingAttribution,
)
from business.marketing.schemas.validation_schemas import (
    AssumptionCreate,
    AssumptionUpdate,
    AssumptionResponse,
    EvidenceCreate,
    EvidenceResponse,
    KnowledgeStatementCreate,
    KnowledgeStatementResponse,
    AssumptionsSummaryResponse,
    AIExtractAssumptionsRequest,
    AIExtractAssumptionsResponse,
    ProjectCanvasesStatusResponse,
    ExtractedAssumptionItem,
    AIDesignExperimentRequest,
    AIDesignExperimentResponse,
    ScaleWarningCheckRequest,
    ScaleWarningCheckResponse,
    CompleteValidationExperimentRequest,
    CompleteValidationExperimentResponse,
    CustomerInterviewCreate,
    CustomerInterviewResponse,
    AIExtractInterviewRequest,
    AIExtractInterviewResponse,
    MarketingAttributionCreate,
    MarketingAttributionResponse,
    AIEvaluateLearningLoopRequest,
    AIEvaluateLearningLoopResponse,
    CreateLearningAndDecisionRequest,
    CreateLearningAndDecisionResponse,
    DecisionLogItemResponse,
    AIProposeCanvasRevisionRequest,
    AIProposeCanvasRevisionResponse,
    CanvasRevisionCreateProposalRequest,
    CanvasRevisionResponse,
)
from business.marketing.services.assumption_service import AssumptionService
from business.marketing.services.ai_assumption_extractor import AIAssumptionExtractor
from business.marketing.services.canvas_evaluator_service import CanvasEvaluatorService
from business.marketing.services.experiment_designer_service import ExperimentDesignerService
from business.marketing.services.interview_service import InterviewService
from business.marketing.services.learning_loop_service import LearningLoopService
from business.marketing.services.canvas_revision_service import CanvasRevisionService
from business.marketing.routers.cockpit_router import resolve_brain_id


router = APIRouter(prefix="", tags=["marketing-validation"])


@router.get("/assumptions", response_model=List[AssumptionResponse])
def list_assumptions(
    project_id: Optional[int] = Query(None, description="Lọc theo project ID"),
    category: Optional[str] = Query(None, description="Lọc theo category (customer, problem, pricing,...)"),
    status: Optional[str] = Query(None, description="Lọc theo status (untested, testing, supported,...)"),
    min_criticality: Optional[int] = Query(None, description="Lọc điểm criticality tối thiểu"),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách các giả định kinh doanh (Assumptions), sắp xếp theo mức độ rủi ro Criticality giảm dần.
    """
    assumptions = AssumptionService.get_assumptions(
        db=db,
        workspace_id=member.workspace_id,
        project_id=project_id,
        category=category,
        status=status,
        min_criticality=min_criticality,
    )
    return assumptions


@router.post("/assumptions", response_model=AssumptionResponse, status_code=status.HTTP_201_CREATED)
def create_assumption(
    payload: AssumptionCreate,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Tạo mới một Assumption trong hệ thống.
    """
    resolved_brain_id = resolve_brain_id(db, member.workspace_id, brain_id)
    assumption = AssumptionService.create_assumption(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=resolved_brain_id,
        data=payload,
    )
    db.commit()
    db.refresh(assumption)
    return assumption


@router.get("/assumptions/summary", response_model=AssumptionsSummaryResponse)
def get_assumptions_summary(
    project_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Lấy thống kê tổng quan về các giả định cho Marketing Cockpit và Hologram Hub.
    """
    summary = AssumptionService.get_assumptions_summary(
        db=db,
        workspace_id=member.workspace_id,
        project_id=project_id,
    )
    return summary


@router.get("/assumptions/{assumption_id}", response_model=AssumptionResponse)
def get_assumption(
    assumption_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Chi tiết một giả định kinh doanh.
    """
    assumption = db.query(Assumption).filter(
        Assumption.id == assumption_id,
        Assumption.workspace_id == member.workspace_id,
    ).first()
    if not assumption or getattr(assumption, "workspace_id", None) != member.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assumption not found")
    return assumption


@router.patch("/assumptions/{assumption_id}", response_model=AssumptionResponse)
def update_assumption(
    assumption_id: int,
    payload: AssumptionUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Cập nhật giả định (impact, uncertainty, confidence, status, rationale,...).
    """
    assumption = db.query(Assumption).filter(
        Assumption.id == assumption_id,
        Assumption.workspace_id == member.workspace_id,
    ).first()
    if not assumption or getattr(assumption, "workspace_id", None) != member.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assumption not found")

    updated = AssumptionService.update_assumption(db=db, assumption=assumption, data=payload)
    db.commit()
    db.refresh(updated)
    return updated


@router.delete("/assumptions/{assumption_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assumption(
    assumption_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Xóa một giả định kinh doanh.
    """
    assumption = db.query(Assumption).filter(
        Assumption.id == assumption_id,
        Assumption.workspace_id == member.workspace_id,
    ).first()
    if not assumption or getattr(assumption, "workspace_id", None) != member.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assumption not found")
    
    db.delete(assumption)
    db.commit()
    return None


@router.post("/knowledge-statements", response_model=KnowledgeStatementResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_statement(
    payload: KnowledgeStatementCreate,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Tạo mới một Knowledge Statement với phân loại Epistemic Status (Fact, Evidence, Inference, Assumption).
    """
    resolved_brain_id = resolve_brain_id(db, member.workspace_id, brain_id)
    statement = AssumptionService.create_knowledge_statement(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=resolved_brain_id,
        data=payload,
    )
    db.commit()
    db.refresh(statement)
    return statement


@router.get("/knowledge-statements", response_model=List[KnowledgeStatementResponse])
def list_knowledge_statements(
    project_id: Optional[int] = Query(None),
    epistemic_status: Optional[str] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Danh sách các phát biểu tri thức của project.
    """
    query = db.query(KnowledgeStatement).filter(KnowledgeStatement.workspace_id == member.workspace_id)
    if project_id is not None:
        query = query.filter(KnowledgeStatement.project_id == project_id)
    if epistemic_status:
        query = query.filter(KnowledgeStatement.epistemic_status == epistemic_status)
    return list(query.all())


@router.post("/evidence", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
def create_evidence(
    payload: EvidenceCreate,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Tạo một Evidence và tự động cập nhật trạng thái các Assumption được liên kết.
    """
    resolved_brain_id = resolve_brain_id(db, member.workspace_id, brain_id)
    evidence, _ = AssumptionService.create_evidence(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=resolved_brain_id,
        data=payload,
    )
    db.commit()
    db.refresh(evidence)
    return evidence


@router.get("/evidence", response_model=List[EvidenceResponse])
def list_evidence(
    project_id: Optional[int] = Query(None),
    source_type: Optional[str] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Danh sách các bằng chứng thu thập được.
    """
    query = db.query(Evidence).filter(Evidence.workspace_id == member.workspace_id)
    if project_id is not None:
        query = query.filter(Evidence.project_id == project_id)
    if source_type:
        query = query.filter(Evidence.source_type == source_type)
    return list(query.all())


@router.post("/ai/extract-assumptions", response_model=AIExtractAssumptionsResponse)
def extract_assumptions_ai(
    payload: AIExtractAssumptionsRequest,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    AI Service trích xuất và xếp hạng rủi ro các giả định (Claims & Assumptions) theo Prompt mẫu §18 trong E3.md.
    """
    resolved_brain_id = resolve_brain_id(db, member.workspace_id, brain_id)
    
    if payload.text:
        res = AIAssumptionExtractor.extract_from_text(
            text=payload.text,
            project_id=payload.project_id,
            canvas_id=payload.canvas_type,
        )
    elif payload.canvas_type and payload.canvas_data:
        items = AIAssumptionExtractor.extract_from_canvas(
            canvas_type=payload.canvas_type,
            canvas_data=payload.canvas_data,
            project_id=payload.project_id,
        )
        res = {
            "system_prompt": AIAssumptionExtractor.extract_from_text("x")["system_prompt"],
            "knowledge_statements": [],
            "assumptions": items,
            "total_extracted": len(items),
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cần cung cấp 'text' hoặc ('canvas_type' và 'canvas_data')",
        )

    saved_count = 0
    if payload.save_to_db and res.get("assumptions"):
        for a_item in res["assumptions"]:
            AssumptionService.create_assumption(
                db=db,
                workspace_id=member.workspace_id,
                brain_id=resolved_brain_id,
                data=AssumptionCreate(
                    statement=a_item["statement"],
                    category=a_item["category"],
                    project_id=payload.project_id,
                    canvas_id=payload.canvas_type,
                    impact=a_item["impact"],
                    uncertainty=a_item["uncertainty"],
                    rationale=a_item.get("rationale"),
                ),
            )
            saved_count += 1
        db.commit()

    return {
        "system_prompt": res["system_prompt"],
        "knowledge_statements": res.get("knowledge_statements", []),
        "assumptions": res["assumptions"],
        "total_extracted": len(res["assumptions"]),
        "saved_count": saved_count,
    }


@router.get("/canvases/status", response_model=ProjectCanvasesStatusResponse)
def get_canvases_status(
    project_id: Optional[int] = Query(None),
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Lấy trạng thái Epistemic (draft, hypothesis, testing, evidence_backed, contradicted) của 4 Canvas Ground Truth.
    """
    resolved_brain_id = resolve_brain_id(db, member.workspace_id, brain_id)
    return CanvasEvaluatorService.evaluate_project_canvases(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=resolved_brain_id,
        project_id=project_id,
    )


@router.post("/ai/design-experiment", response_model=AIDesignExperimentResponse)
def design_experiment_ai(
    payload: AIDesignExperimentRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    AI Service thiết kế thử nghiệm nhỏ nhất (Smallest Useful Experiment) theo Prompt mẫu §27 trong E3.md.
    """
    statement = payload.assumption_statement
    category = payload.category or "customer"
    impact = payload.impact or 4
    uncertainty = payload.uncertainty or 4

    if payload.assumption_id:
        asm = db.query(Assumption).filter(
            Assumption.id == payload.assumption_id,
            Assumption.workspace_id == member.workspace_id,
        ).first()
        if not asm:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assumption not found")
        statement = asm.statement
        category = asm.category
        impact = asm.impact
        uncertainty = asm.uncertainty

    if not statement:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cần cung cấp 'assumption_id' hoặc 'assumption_statement'",
        )

    res = ExperimentDesignerService.design_smallest_experiment(
        assumption_statement=statement,
        category=category,
        impact=impact,
        uncertainty=uncertainty,
    )
    return res


@router.post("/scale-warning-check", response_model=ScaleWarningCheckResponse)
def check_scale_warning(
    payload: ScaleWarningCheckRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Kiểm tra rủi ro trước khi Scale Campaign (§30, §52 trong E3.md) - Soft Warning (Founder can Continue Anyway).
    """
    asm = db.query(Assumption).filter(
        Assumption.id == payload.assumption_id,
        Assumption.workspace_id == member.workspace_id,
    ).first()
    if not asm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assumption not found")

    warning_info = ExperimentDesignerService.evaluate_scale_warning(assumption=asm)
    return warning_info


@router.post("/experiments/{experiment_id}/complete", response_model=CompleteValidationExperimentResponse)
def complete_validation_experiment(
    experiment_id: int,
    payload: CompleteValidationExperimentRequest,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Hoàn tất Experiment: tự động ghi nhận Evidence, cập nhật Assumption status & sinh kết quả có cấu trúc (§25, §36, §102).
    """
    resolved_brain_id = resolve_brain_id(db, member.workspace_id, brain_id)
    exp = db.query(MarketingExperiment).filter(
        MarketingExperiment.id == experiment_id,
        MarketingExperiment.workspace_id == member.workspace_id,
    ).first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    updated_exp, evidence, updated_asm = ExperimentDesignerService.complete_experiment(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=resolved_brain_id,
        experiment=exp,
        conclusion=payload.conclusion,
        observations=payload.observations,
        learning_summary=payload.learning_summary,
    )
    db.commit()

    return {
        "experiment_id": str(updated_exp.id),
        "status": updated_exp.status,
        "conclusion": updated_exp.conclusion or payload.conclusion,
        "learning": updated_exp.learning or payload.learning_summary,
        "evidence_id": str(evidence.id) if evidence else None,
        "assumption_id": str(updated_asm.id) if updated_asm else None,
        "assumption_status": updated_asm.status if updated_asm else None,
        "assumption_confidence": updated_asm.confidence if updated_asm else None,
    }


@router.post("/crm/interviews", response_model=CustomerInterviewResponse, status_code=status.HTTP_201_CREATED)
def record_customer_interview(
    payload: CustomerInterviewCreate,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Lưu trữ phỏng vấn khách hàng (Customer Interview) và tự động sinh Evidence cho các giả định liên quan (§35, §101).
    """
    resolved_brain_id = resolve_brain_id(db, member.workspace_id, brain_id)
    interview, _ = InterviewService.record_interview_and_generate_evidence(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=resolved_brain_id,
        project_id=payload.project_id,
        contact_id=payload.contact_id,
        customer_name=payload.customer_name,
        segment=payload.segment,
        pains=payload.pains,
        alternatives=payload.alternatives,
        objections=payload.objections,
        willingness_to_pay=payload.willingness_to_pay,
        notable_quotes=payload.notable_quotes,
        notes=payload.notes,
    )
    db.commit()
    db.refresh(interview)
    return interview


@router.get("/crm/interviews", response_model=List[CustomerInterviewResponse])
def list_customer_interviews(
    project_id: Optional[int] = Query(None),
    contact_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Danh sách các cuộc phỏng vấn khách hàng.
    """
    query = db.query(CustomerInterview).filter(CustomerInterview.workspace_id == member.workspace_id)
    if project_id is not None:
        query = query.filter(CustomerInterview.project_id == project_id)
    if contact_id is not None:
        query = query.filter(CustomerInterview.contact_id == contact_id)
    return list(query.order_by(CustomerInterview.interview_date.desc()).all())


@router.post("/ai/extract-interview", response_model=AIExtractInterviewResponse)
def extract_interview_ai(
    payload: AIExtractInterviewRequest,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    AI trích xuất cấu trúc tín hiệu khách hàng (Pain Signals, Objections, Willingness-to-pay, Quotes) từ transcript thô (§35).
    """
    resolved_brain_id = resolve_brain_id(db, member.workspace_id, brain_id)
    extracted = InterviewService.extract_interview_from_transcript(
        transcript_text=payload.transcript,
        customer_name=payload.customer_name,
        segment=payload.segment or "ICP Target",
    )

    saved_id = None
    evidence_count = 0
    if payload.save_to_db:
        interview, ev_list = InterviewService.record_interview_and_generate_evidence(
            db=db,
            workspace_id=member.workspace_id,
            brain_id=resolved_brain_id,
            project_id=payload.project_id,
            contact_id=payload.contact_id,
            customer_name=extracted["customer_name"],
            segment=extracted["segment"],
            pains=extracted["pains"],
            alternatives=extracted["alternatives"],
            objections=extracted["objections"],
            willingness_to_pay=extracted["willingness_to_pay"],
            notable_quotes=extracted["notable_quotes"],
        )
        db.commit()
        saved_id = str(interview.id)
        evidence_count = len(ev_list)

    return {
        "customer_name": extracted["customer_name"],
        "segment": extracted["segment"],
        "interview_date": extracted["interview_date"],
        "pains": extracted["pains"],
        "alternatives": extracted["alternatives"],
        "objections": extracted["objections"],
        "willingness_to_pay": extracted["willingness_to_pay"],
        "notable_quotes": extracted["notable_quotes"],
        "saved_interview_id": saved_id,
        "generated_evidence_count": evidence_count,
    }


@router.post("/crm/attributions", response_model=MarketingAttributionResponse, status_code=status.HTTP_201_CREATED)
def record_marketing_attribution(
    payload: MarketingAttributionCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Ghi nhận nguồn gốc tiếp thị (Marketing Attribution: Lead -> Experiment -> Assumption) (§58, §59).
    """
    attr = InterviewService.record_attribution(
        db=db,
        workspace_id=member.workspace_id,
        contact_id=payload.contact_id,
        lead_id=payload.lead_id,
        campaign_id=payload.campaign_id,
        experiment_id=payload.experiment_id,
        variant_id=payload.variant_id,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        utm_content=payload.utm_content,
        utm_term=payload.utm_term,
    )
    db.commit()
    db.refresh(attr)
    return attr


@router.get("/crm/attributions", response_model=List[MarketingAttributionResponse])
def list_marketing_attributions(
    experiment_id: Optional[int] = Query(None),
    campaign_id: Optional[int] = Query(None),
    contact_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Danh sách dữ liệu Attribution theo chiến dịch hoặc thử nghiệm.
    """
    query = db.query(MarketingAttribution).filter(MarketingAttribution.workspace_id == member.workspace_id)
    if experiment_id is not None:
        query = query.filter(MarketingAttribution.experiment_id == experiment_id)
    if campaign_id is not None:
        query = query.filter(MarketingAttribution.campaign_id == campaign_id)
    if contact_id is not None:
        query = query.filter(MarketingAttribution.contact_id == contact_id)
    return list(query.order_by(MarketingAttribution.created_at.desc()).all())


@router.post("/ai/evaluate-learning-loop", response_model=AIEvaluateLearningLoopResponse)
def evaluate_learning_loop_ai(
    payload: AIEvaluateLearningLoopRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    AI tổng hợp và trả lời 5 câu hỏi cốt lõi của Vòng lặp Học hỏi (Learning Loop) (§36).
    """
    exp = None
    if payload.experiment_id:
        exp = db.query(MarketingExperiment).filter(
            MarketingExperiment.id == payload.experiment_id,
            MarketingExperiment.workspace_id == member.workspace_id,
        ).first()

    asm = None
    if payload.assumption_id:
        asm = db.query(Assumption).filter(
            Assumption.id == payload.assumption_id,
            Assumption.workspace_id == member.workspace_id,
        ).first()

    res = LearningLoopService.evaluate_learning_loop(
        experiment=exp,
        assumption=asm,
        observations=payload.observations,
        actual_outcome=payload.actual_outcome,
    )
    return res


@router.post("/learning-loop/decisions", response_model=CreateLearningAndDecisionResponse, status_code=status.HTTP_201_CREATED)
def record_learning_and_decision_endpoint(
    payload: CreateLearningAndDecisionRequest,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Lưu Learning Object (§37) và ghi vào Decision Journal (§38, §39, §53).
    """
    resolved_brain_id = resolve_brain_id(db, member.workspace_id, brain_id)
    learning_obj, decision_log = LearningLoopService.record_learning_and_decision(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=resolved_brain_id,
        project_id=payload.project_id,
        experiment_id=payload.experiment_id,
        campaign_id=payload.campaign_id,
        summary=payload.summary,
        observation=payload.observation or "",
        hypothesis=payload.hypothesis or "",
        action=payload.action or "",
        result=payload.result or "",
        learning=payload.learning,
        affected_assumption_ids=payload.affected_assumption_ids,
        evidence_ids=payload.evidence_ids,
        decision_recommendation=payload.decision_recommendation,
        create_decision_log=payload.create_decision_log,
        decision_question=payload.decision_question,
        decision_text=payload.decision_text,
        decision_reason=payload.decision_reason,
        next_action=payload.next_action,
        owner=payload.owner,
    )
    db.commit()

    return {
        "learning_id": str(learning_obj.id),
        "summary": learning_obj.summary or learning_obj.learning,
        "decision_recommendation": learning_obj.decision_recommendation or "continue",
        "decision_log_id": str(decision_log.id) if decision_log else None,
        "decision_title": decision_log.title if decision_log else None,
        "decision_text": decision_log.decision if decision_log else None,
    }


@router.get("/decisions", response_model=List[DecisionLogItemResponse])
def list_decision_log_items(
    project_id: Optional[int] = Query(None),
    experiment_id: Optional[int] = Query(None),
    campaign_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Truy vấn Decision Log (§38, §39, §53).
    """
    query = db.query(MarketingDecision).filter(MarketingDecision.workspace_id == member.workspace_id)
    if project_id is not None:
        query = query.filter(MarketingDecision.project_id == project_id)
    if experiment_id is not None:
        query = query.filter(MarketingDecision.experiment_id == experiment_id)
    if campaign_id is not None:
        query = query.filter(MarketingDecision.campaign_id == campaign_id)
    return list(query.order_by(MarketingDecision.created_at.desc()).all())


@router.post("/ai/propose-canvas-revision", response_model=AIProposeCanvasRevisionResponse)
def propose_canvas_revision_ai(
    payload: AIProposeCanvasRevisionRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """
    AI đề xuất cập nhật Ground Truth Canvas dựa trên Evidence/Learning mới (§42).
    """
    return CanvasRevisionService.propose_revision_from_evidence(
        canvas_type=payload.canvas_type,
        current_canvas=payload.current_canvas,
        evidence_statement=payload.evidence_statement,
        is_contradiction=payload.is_contradiction,
        affected_field=payload.affected_field,
    )


@router.post("/canvases/revisions", response_model=CanvasRevisionResponse, status_code=status.HTTP_201_CREATED)
def create_canvas_revision_proposal(
    payload: CanvasRevisionCreateProposalRequest,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Tạo Canvas Revision Request / Proposal (§41, §43) cần Founder phê duyệt trước khi áp dụng.
    """
    resolved_brain_id = resolve_brain_id(db, member.workspace_id, brain_id)
    rev = CanvasRevisionService.create_revision_proposal(
        db=db,
        workspace_id=member.workspace_id,
        brain_id=resolved_brain_id,
        project_id=payload.project_id,
        canvas_type=payload.canvas_type,
        changed_fields=payload.changed_fields,
        previous_snapshot=payload.previous_snapshot,
        new_snapshot=payload.new_snapshot,
        reason=payload.reason,
        evidence_ids=payload.evidence_ids,
        auto_approve=payload.auto_approve,
        approved_by=member.user_id if payload.auto_approve else None,
    )
    db.commit()
    db.refresh(rev)
    return rev


@router.get("/canvases/revisions", response_model=List[CanvasRevisionResponse])
def list_canvas_revisions(
    project_id: Optional[int] = Query(None),
    canvas_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Lịch sử cập nhật Canvas Revision History (§41).
    """
    query = db.query(CanvasRevision).filter(CanvasRevision.workspace_id == member.workspace_id)
    if project_id is not None:
        query = query.filter(CanvasRevision.project_id == project_id)
    if canvas_type is not None:
        query = query.filter(CanvasRevision.canvas_type == canvas_type)
    if status is not None:
        query = query.filter(CanvasRevision.status == status)
    return list(query.order_by(CanvasRevision.created_at.desc()).all())


@router.post("/canvases/revisions/{revision_id}/approve", response_model=CanvasRevisionResponse)
def approve_canvas_revision(
    revision_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Founder phê duyệt áp dụng cập nhật Canvas (§41, §103).
    """
    rev = CanvasRevisionService.approve_revision(
        db=db,
        workspace_id=member.workspace_id,
        revision_id=revision_id,
        approved_by=member.user_id,
    )
    if not rev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision proposal not found")
    db.commit()
    db.refresh(rev)
    return rev


@router.post("/canvases/revisions/{revision_id}/reject", response_model=CanvasRevisionResponse)
def reject_canvas_revision(
    revision_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Founder từ chối đề xuất cập nhật Canvas.
    """
    rev = CanvasRevisionService.reject_revision(
        db=db,
        workspace_id=member.workspace_id,
        revision_id=revision_id,
    )
    if not rev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision proposal not found")
    db.commit()
    db.refresh(rev)
    return rev





