"""API Router for Multi-Regime Accounting Management & Transitions (TT58 & TT199)."""
from datetime import date
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.business.finance.regime_resolver import AccountingRegimeResolver, REGIME_TT58, REGIME_TT199
from app.business.finance.transition_engine import AccountingTransitionEngine

router = APIRouter()
resolver = AccountingRegimeResolver()
transition_engine = AccountingTransitionEngine()


class TransitionPreviewRequest(BaseModel):
    from_fiscal_year: int = Field(..., description="Năm tài chính cũ cần chốt sổ, vd: 2025")
    to_fiscal_year: int = Field(..., description="Năm tài chính mới bắt đầu áp dụng, vd: 2026")
    to_regulation: str = Field(REGIME_TT199, description="Chế độ kế toán đích: TT199_2026 hoặc TT58_2026")


class TransitionExecuteRequest(BaseModel):
    from_fiscal_year: int = Field(..., description="Năm tài chính cũ")
    to_fiscal_year: int = Field(..., description="Năm tài chính mới")
    to_regulation: str = Field(REGIME_TT199, description="Chế độ kế toán đích")
    notes: Optional[str] = Field(None, description="Ghi chú lý do chuyển đổi chế độ kế toán")


def _guard(workspace_id: int, member: WorkspaceMember) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden: Invalid workspace context")


def _guard_founder(workspace_id: int, member: WorkspaceMember) -> None:
    _guard(workspace_id, member)
    role = getattr(member, "role", "MEMBER").upper()
    if role not in ["ADMIN", "OWNER", "FOUNDER", "CHIEF_ACCOUNTANT"]:
        raise HTTPException(status_code=403, detail="Founder, Owner or Chief Accountant privilege required")


@router.get("/available", summary="Liệt kê danh sách các chế độ kế toán khả dụng (TT58, TT199)")
def list_available_regimes(
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    _guard(workspace_id, member)
    regimes = resolver.get_available_regimes()
    return {"status": "success", "data": regimes}


@router.get("/history", summary="Lấy lịch sử chế độ kế toán theo từng năm tài chính của doanh nghiệp")
async def list_fiscal_year_history(
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: AsyncSession = Depends(get_db),
):
    _guard(workspace_id, member)
    history = await resolver.list_fiscal_year_history(db, workspace_id)
    return {"status": "success", "data": history}


@router.get("/current", summary="Lấy chi tiết chế độ kế toán và hệ thống tài khoản cho niên độ")
async def get_current_regime(
    workspace_id: int = Query(...),
    fiscal_year: Optional[int] = Query(None, description="Năm tài chính (mặc định năm hiện tại)"),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: AsyncSession = Depends(get_db),
):
    _guard(workspace_id, member)
    target_year = fiscal_year or date.today().year
    profile = await resolver.get_or_create_fiscal_profile(db, workspace_id, target_year)
    coa = resolver.get_chart_of_accounts(profile.regulation_code)

    return {
        "status": "success",
        "data": {
            "workspace_id": workspace_id,
            "fiscal_year": profile.fiscal_year,
            "regulation_code": profile.regulation_code,
            "mode": profile.mode,
            "status": profile.status,
            "is_locked": profile.status in ["LOCKED", "ARCHIVED"],
            "chart_of_accounts": coa,
        },
    }


@router.post("/transition/preview", summary="Xem trước bảng ánh xạ số dư đầu kỳ khi chuyển đổi chế độ kế toán")
async def preview_regime_transition(
    payload: TransitionPreviewRequest,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: AsyncSession = Depends(get_db),
):
    _guard_founder(workspace_id, member)
    preview = await transition_engine.preview_transition(
        db=db,
        workspace_id=workspace_id,
        from_year=payload.from_fiscal_year,
        to_year=payload.to_fiscal_year,
        to_regulation=payload.to_regulation,
    )
    return {"status": "success", "data": preview}


@router.post("/transition/execute", summary="Thực thi chuyển đổi chế độ kế toán và khóa sổ niên độ cũ")
async def execute_regime_transition(
    payload: TransitionExecuteRequest,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: AsyncSession = Depends(get_db),
):
    _guard_founder(workspace_id, member)
    result = await transition_engine.execute_transition(
        db=db,
        workspace_id=workspace_id,
        from_year=payload.from_fiscal_year,
        to_year=payload.to_fiscal_year,
        to_regulation=payload.to_regulation,
        user_id=member.user_id,
        notes=payload.notes,
    )
    return {"status": "success", "data": result}
