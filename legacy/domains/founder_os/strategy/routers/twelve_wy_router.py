from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.session import get_db
from core.auth import get_current_workspace_member
from platform_core.auth.models import WorkspaceMember
from founder_os.strategy.schemas.twelve_wy_schemas import (
    TwelveWeekCycleCreate,
    TwelveWeekCycleResponse,
    TacticalItemCreate,
    TacticalItemUpdate,
    TacticalItemResponse,
    WeeklyReviewResponse,
    TwelveWyDashboardResponse,
)
from founder_os.strategy.services.twelve_wy_service import TwelveWyService

router = APIRouter(prefix="/12wy", tags=["12-Week Year Strategic Execution Loop"])


@router.get("/dashboard/{project_id}", response_model=TwelveWyDashboardResponse)
def get_12wy_dashboard(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Lấy toàn cảnh chu kỳ thực thi 12 tuần & điểm số kỷ luật lead indicator."""
    return TwelveWyService.get_cycle_dashboard(db, member.workspace_id, project_id)


@router.post("/cycle", response_model=TwelveWeekCycleResponse)
def create_or_get_cycle(
    payload: TwelveWeekCycleCreate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Khởi tạo hoặc lấy chu kỳ 12 tuần đang hoạt động."""
    return TwelveWyService.get_or_create_active_cycle(
        db, member.workspace_id, payload.project_id, payload.title
    )


@router.post("/tactics", response_model=TacticalItemResponse)
def create_tactical_item(
    payload: TacticalItemCreate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Thêm hành động chiến thuật tuần (12WY Tactic) kèm chỉ số dẫn dắt (Lead Indicator)."""
    return TwelveWyService.create_tactic(db, member.workspace_id, payload)


@router.put("/tactics/{tactic_id}", response_model=TacticalItemResponse)
def update_tactical_item(
    tactic_id: int,
    payload: TacticalItemUpdate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Cập nhật tiến độ chỉ số dẫn dắt (actual_count) hoặc trạng thái hoàn thành."""
    return TwelveWyService.update_tactic(db, member.workspace_id, tactic_id, payload)


@router.post("/weekly-review/{cycle_id}/{week_number}", response_model=WeeklyReviewResponse)
def generate_weekly_review(
    cycle_id: int,
    week_number: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Tổng kết phiên kiểm điểm tiến độ tuần (WAM) và đưa ra khuyến nghị AI."""
    return TwelveWyService.generate_weekly_review(
        db, member.workspace_id, cycle_id, week_number
    )
