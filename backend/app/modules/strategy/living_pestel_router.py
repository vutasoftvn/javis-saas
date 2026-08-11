from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.core.feature_flags import require_flag, FLAG_LIVING_PESTEL_V12
from app.db.models import WorkspaceMember
from app.modules.strategy.living_pestel_service import LivingPestelService

router = APIRouter()


class PestelSignalIngest(BaseModel):
    signal_title: str
    pestel_category: str  # POLITICAL, ECONOMIC, SOCIAL, TECHNOLOGICAL, ENVIRONMENTAL, LEGAL
    magnitude: str  # LOW, MEDIUM, HIGH, CRITICAL
    signal_summary: Optional[str] = None


class ModelRunAuditCreate(BaseModel):
    model_profile: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    status: str = "success"


class ModelProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    temperature: Optional[float] = None
    is_active: Optional[bool] = None


@router.post("/pestel-signals")
def ingest_pestel_signal(
    workspace_id: int,
    data: PestelSignalIngest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Tiếp nhận tín hiệu Living PESTEL vĩ mô và kích hoạt Material Change Flow (Spec §48)."""
    require_flag(db, FLAG_LIVING_PESTEL_V12, workspace_id)
    service = LivingPestelService(db, workspace_id, member.user_id)
    return service.ingest_signal(
        signal_title=data.signal_title,
        pestel_category=data.pestel_category,
        magnitude=data.magnitude,
        signal_summary=data.signal_summary,
    )


@router.get("/pestel-signals")
def get_pestel_signals(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Lấy danh sách các tín hiệu vĩ mô Living PESTEL."""
    require_flag(db, FLAG_LIVING_PESTEL_V12, workspace_id)
    service = LivingPestelService(db, workspace_id, member.user_id)
    return {"signals": service.get_pestel_signals()}


@router.get("/model-runs/audit")
def get_model_runs_audit(
    workspace_id: int,
    limit: int = 20,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Lấy lịch sử kiểm toán thực thi các mô hình AI (Model Runs Audit Table)."""
    require_flag(db, FLAG_LIVING_PESTEL_V12, workspace_id)
    service = LivingPestelService(db, workspace_id, member.user_id)
    return {"audits": service.get_model_runs(limit=limit)}


@router.post("/model-runs/audit")
def record_model_run_audit(
    workspace_id: int,
    data: ModelRunAuditCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Ghi nhận nhật ký kiểm toán thực thi AI."""
    require_flag(db, FLAG_LIVING_PESTEL_V12, workspace_id)
    service = LivingPestelService(db, workspace_id, member.user_id)
    return service.record_model_run(
        model_profile=data.model_profile,
        prompt_tokens=data.prompt_tokens,
        completion_tokens=data.completion_tokens,
        latency_ms=data.latency_ms,
        status_val=data.status,
    )


@router.get("/model-profiles")
def get_model_profiles(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Lấy danh sách các Model Profile AI khả dụng cho Terra & mCOSA V12 (Spec §56)."""
    require_flag(db, FLAG_LIVING_PESTEL_V12, workspace_id)
    service = LivingPestelService(db, workspace_id, member.user_id)
    return {"profiles": service.list_model_profiles()}


@router.put("/model-profiles/{profile_id}")
def update_model_profile(
    profile_id: str,
    workspace_id: int,
    data: ModelProfileUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Cập nhật cấu hình Model Profile AI (display_name/temperature/is_active)."""
    require_flag(db, FLAG_LIVING_PESTEL_V12, workspace_id)
    service = LivingPestelService(db, workspace_id, member.user_id)
    return service.update_model_profile(
        profile_id,
        display_name=data.display_name,
        temperature=data.temperature,
        is_active=data.is_active,
    )
