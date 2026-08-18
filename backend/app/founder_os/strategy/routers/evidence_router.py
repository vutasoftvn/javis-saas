from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.platform.auth.models import WorkspaceMember
from app.founder_os.strategy.schemas.evidence_schemas import (
    HypothesisCreate,
    HypothesisUpdate,
    HypothesisResponse,
    EvidenceCreate,
    EvidenceResponse,
    StrategicDecisionCreate,
    StrategicDecisionResponse,
    AssumptionMatrixResponse,
)
from app.founder_os.strategy.services.evidence_engine_service import EvidenceEngineService
from app.founder_os.strategy.services.decision_log_service import DecisionLogService

router = APIRouter(prefix="/evidence", tags=["COSA Assumption & Evidence Backbone"])


# --- Hypotheses Endpoints ---

@router.get("/hypotheses", response_model=List[HypothesisResponse])
def list_hypotheses(
    project_id: Optional[int] = Query(None, description="Lọc theo Project ID"),
    category: Optional[str] = Query(None, description="Lọc theo category"),
    status: Optional[str] = Query(None, description="Lọc theo status"),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    """Lấy danh sách Giả định (Hypotheses) của Workspace/Project."""
    service = EvidenceEngineService(db=db, workspace_id=member.workspace_id, user_id=member.user_id)
    return service.list_hypotheses(project_id=project_id, category=category, status=status)


@router.post("/hypotheses", response_model=HypothesisResponse, status_code=status.HTTP_201_CREATED)
def create_hypothesis(
    payload: HypothesisCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    """Tạo mới một Giả định cho Project."""
    service = EvidenceEngineService(db=db, workspace_id=member.workspace_id, user_id=member.user_id)
    return service.create_hypothesis(payload)


@router.patch("/hypotheses/{hypothesis_id}", response_model=HypothesisResponse)
def update_hypothesis(
    hypothesis_id: int,
    payload: HypothesisUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    """Cập nhật Giả định."""
    service = EvidenceEngineService(db=db, workspace_id=member.workspace_id, user_id=member.user_id)
    res = service.update_hypothesis(hypothesis_id, payload)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hypothesis not found")
    return res


@router.delete("/hypotheses/{hypothesis_id}")
def delete_hypothesis(
    hypothesis_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    """Xóa Giả định."""
    service = EvidenceEngineService(db=db, workspace_id=member.workspace_id, user_id=member.user_id)
    if not service.delete_hypothesis(hypothesis_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hypothesis not found")
    return {"status": "deleted", "id": hypothesis_id}


@router.get("/matrix/{project_id}", response_model=AssumptionMatrixResponse)
def get_assumption_matrix(
    project_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    """Lấy Ma trận Rủi ro Giả định 4 góc phần tư (Importance vs Uncertainty)."""
    service = EvidenceEngineService(db=db, workspace_id=member.workspace_id, user_id=member.user_id)
    return service.get_assumption_matrix(project_id=project_id)


# --- Evidences Endpoints ---

@router.get("/evidences", response_model=List[EvidenceResponse])
def list_evidences(
    project_id: Optional[int] = Query(None, description="Lọc theo Project ID"),
    ladder_level: Optional[str] = Query(None, description="Lọc theo nấc thang E0-E6"),
    type: Optional[str] = Query(None, description="Lọc theo loại bằng chứng"),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    """Lấy danh sách Bằng chứng (Evidences) thực tế."""
    service = EvidenceEngineService(db=db, workspace_id=member.workspace_id, user_id=member.user_id)
    return service.list_evidences(project_id=project_id, ladder_level=ladder_level, type=type)


@router.post("/evidences", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
def create_evidence(
    payload: EvidenceCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    """Ghi nhận Bằng chứng mới và tự động tái tính điểm cho các Giả định liên quan."""
    service = EvidenceEngineService(db=db, workspace_id=member.workspace_id, user_id=member.user_id)
    return service.create_evidence(payload)


@router.delete("/evidences/{evidence_id}")
def delete_evidence(
    evidence_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    """Xóa Bằng chứng."""
    service = EvidenceEngineService(db=db, workspace_id=member.workspace_id, user_id=member.user_id)
    if not service.delete_evidence(evidence_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    return {"status": "deleted", "id": evidence_id}


# --- Decisions & Company Memory Endpoints ---

@router.get("/decisions", response_model=List[StrategicDecisionResponse])
def list_decisions(
    project_id: Optional[int] = Query(None, description="Lọc theo Project ID"),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    """Lấy danh sách Quyết định Chiến lược."""
    service = DecisionLogService(db=db, workspace_id=member.workspace_id, user_id=member.user_id)
    return service.list_decisions(project_id=project_id)


@router.post("/decisions", response_model=StrategicDecisionResponse, status_code=status.HTTP_201_CREATED)
def record_decision(
    payload: StrategicDecisionCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    """Ghi nhận Quyết định Chiến lược mới kèm bằng chứng minh chứng (Decision Lineage)."""
    service = DecisionLogService(db=db, workspace_id=member.workspace_id, user_id=member.user_id)
    return service.record_decision(payload)


@router.get("/decisions/memory", response_model=List[Dict[str, Any]])
def query_company_memory(
    query_text: Optional[str] = Query(None, description="Từ khóa tra cứu câu hỏi/lý do quyết định"),
    project_id: Optional[int] = Query(None, description="Lọc theo Project ID"),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    """Tra cứu Bộ Nhớ Quyết Định Công Ty (Company Memory) kèm giải trình bằng chứng."""
    service = DecisionLogService(db=db, workspace_id=member.workspace_id, user_id=member.user_id)
    return service.query_company_memory(query_text=query_text, project_id=project_id)
