from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db
from core.auth import get_current_workspace_member
from platform_core.auth.models import WorkspaceMember
from founder_os.strategy.schemas.lens_schemas import (
    PestelSignalCreate, PestelSignalResponse,
    SwotItemCreate, SwotItemResponse,
    TowsOptionCreate, TowsOptionResponse, TowsToTacticConvertRequest,
    BscGoalCreate, BscGoalResponse,
    StageLensSummaryResponse
)
from founder_os.strategy.schemas.evidence_schemas import HypothesisResponse
from founder_os.strategy.services.strategy_lens_service import StrategyLensService

router = APIRouter(prefix="/lenses", tags=["Strategy Lenses (PESTEL, SWOT, TOWS, BSC)"])


# --- 1. Summary Endpoint ---
@router.get("/summary/{project_id}", response_model=StageLensSummaryResponse)
def get_stage_lens_summary(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Lấy tổng hợp 4 Lăng kính Chiến lược theo đúng Stage của dự án."""
    return StrategyLensService.get_stage_lens_summary_sync(
        db, member.workspace_id, project_id
    )


# --- 2. PESTEL Radar ---
@router.get("/pestel", response_model=List[PestelSignalResponse])
def list_pestel_signals(
    project_id: int = Query(..., description="ID dự án"),
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return StrategyLensService.list_pestel_signals_sync(
        db, member.workspace_id, project_id
    )


@router.post("/pestel", response_model=PestelSignalResponse, status_code=201)
def create_pestel_signal(
    payload: PestelSignalCreate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return StrategyLensService.create_pestel_signal_sync(
        db, member.workspace_id, payload
    )


@router.post("/pestel/{signal_id}/to-hypothesis", response_model=HypothesisResponse)
def convert_pestel_to_hypothesis(
    signal_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Chuyển đổi tín hiệu PESTEL vĩ mô thành Giả định cần kiểm chứng."""
    return StrategyLensService.convert_pestel_to_hypothesis_sync(
        db, member.workspace_id, signal_id
    )


# --- 3. Evidence-backed SWOT ---
@router.get("/swot", response_model=List[SwotItemResponse])
def list_swot_items(
    project_id: int = Query(..., description="ID dự án"),
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return StrategyLensService.list_swot_items_sync(
        db, member.workspace_id, project_id
    )


@router.post("/swot", response_model=SwotItemResponse, status_code=201)
def create_swot_item(
    payload: SwotItemCreate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Thêm một yếu tố SWOT (Điểm Mạnh/Yếu bắt buộc có bằng chứng minh chứng)."""
    return StrategyLensService.create_swot_item_sync(
        db, member.workspace_id, payload
    )


# --- 4. TOWS Matrix & 12WY Tactics ---
@router.get("/tows", response_model=List[TowsOptionResponse])
def list_tows_options(
    project_id: int = Query(..., description="ID dự án"),
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return StrategyLensService.list_tows_options_sync(
        db, member.workspace_id, project_id
    )


@router.post("/tows", response_model=TowsOptionResponse, status_code=201)
def create_tows_option(
    payload: TowsOptionCreate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return StrategyLensService.create_tows_option_sync(
        db, member.workspace_id, payload
    )


@router.post("/tows/{option_id}/generate-tactics", response_model=TowsOptionResponse)
def convert_tows_to_tactics(
    option_id: int,
    payload: TowsToTacticConvertRequest,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Chuyển hóa chiến lược TOWS thành Kế hoạch hành động 12 Tuần & Giả định thực thi."""
    return StrategyLensService.convert_tows_to_tactics_sync(
        db, member.workspace_id, option_id, payload
    )


# --- 5. Balanced Scorecard (BSC) ---
@router.get("/bsc", response_model=List[BscGoalResponse])
def list_bsc_goals(
    project_id: int = Query(..., description="ID dự án"),
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return StrategyLensService.list_bsc_goals_sync(
        db, member.workspace_id, project_id
    )


@router.post("/bsc", response_model=BscGoalResponse, status_code=201)
def create_bsc_goal(
    payload: BscGoalCreate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Thiết lập mục tiêu BSC (Chỉ cho phép từ S5 Operate & Grow)."""
    return StrategyLensService.create_bsc_goal_sync(
        db, member.workspace_id, payload
    )
