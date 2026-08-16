from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.modules.finance import tt58_engine

router = APIRouter()


class CreateDocumentRequest(BaseModel):
    document_no: str = Field(..., description="Số hiệu chứng từ (ví dụ: PT001, PC002, HD003)")
    document_type: str = Field(..., description="Loại chứng từ: PHIEU_THU, PHIEU_CHI, HOA_DON, PHIEU_XUAT")
    document_date: date = Field(default_factory=date.today)
    total_amount: Decimal = Field(..., description="Tổng tiền chứng từ")
    description: str = Field("", description="Nội dung diễn giải chứng từ")
    direction: str = Field("IN", description="Hướng tiền: IN (Thu) | OUT (Chi)")


class PostDocumentRequest(BaseModel):
    amount: Decimal = Field(..., description="Số tiền ghi sổ")
    direction: str = Field("IN", description="IN | OUT")
    description: Optional[str] = None
    category: str = Field("DOANH_THU", description="Phân loại: DOANH_THU, CHI_PHI_VAN_HANH, GIA_VON, v.v.")


class VoidDocumentRequest(BaseModel):
    reason: str = Field(..., description="Lý do hủy chứng từ")


class InventoryValuationRequest(BaseModel):
    opening_qty: Decimal = Field(Decimal("100"), description="Số lượng tồn đầu kỳ")
    opening_val: Decimal = Field(Decimal("10000000"), description="Giá trị tồn đầu kỳ")
    inflow_qty: Decimal = Field(Decimal("200"), description="Số lượng nhập trong kỳ")
    inflow_val: Decimal = Field(Decimal("22000000"), description="Giá trị nhập trong kỳ")


@router.get("/workspaces/{workspace_id}/finance/tt58/metrics/founder-lite")
def get_founder_lite_metrics(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    metrics = tt58_engine.calculate_founder_finance_lite(db, workspace_id)
    return {"status": "success", "data": metrics}


@router.post("/workspaces/{workspace_id}/finance/tt58/documents")
def create_document(
    workspace_id: int,
    payload: CreateDocumentRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    doc = tt58_engine.create_accounting_document(
        db=db,
        workspace_id=workspace_id,
        document_no=payload.document_no,
        document_type=payload.document_type,
        document_date=payload.document_date,
        total_amount=payload.total_amount,
        description=payload.description,
        direction=payload.direction,
    )
    return {
        "status": "success",
        "data": {
            "id": str(doc.id),
            "document_no": doc.document_no,
            "document_type": doc.document_type,
            "document_date": doc.document_date.isoformat(),
            "status": doc.status,
        },
    }


@router.post("/workspaces/{workspace_id}/finance/tt58/documents/{document_id}/post")
def post_document(
    workspace_id: int,
    document_id: str,
    payload: PostDocumentRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    try:
        doc_id = int(document_id)
        res = tt58_engine.post_accounting_document(
            db=db,
            workspace_id=workspace_id,
            document_id=doc_id,
            amount=payload.amount,
            direction=payload.direction,
            description=payload.description or "",
            category=payload.category,
            user_id=member.user_id,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workspaces/{workspace_id}/finance/tt58/documents/{document_id}/void")
def void_document(
    workspace_id: int,
    document_id: str,
    payload: VoidDocumentRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    try:
        doc_id = int(document_id)
        res = tt58_engine.void_accounting_document(
            db=db,
            workspace_id=workspace_id,
            document_id=doc_id,
            reason=payload.reason,
            user_id=member.user_id,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workspaces/{workspace_id}/finance/tt58/inventory/valuation")
def calculate_inventory_valuation(
    workspace_id: int,
    payload: InventoryValuationRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    avg_unit_cost = tt58_engine.calculate_inventory_average_cost(
        opening_qty=payload.opening_qty,
        opening_val=payload.opening_val,
        inflow_qty=payload.inflow_qty,
        inflow_val=payload.inflow_val,
    )
    total_qty = payload.opening_qty + payload.inflow_qty
    total_val = payload.opening_val + payload.inflow_val
    return {
        "status": "success",
        "data": {
            "total_quantity": float(total_qty),
            "total_value": float(total_val),
            "weighted_average_unit_cost": float(avg_unit_cost),
        }
    }


@router.get("/workspaces/{workspace_id}/finance/tt58/reports/b01")
def get_report_b01(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    report = tt58_engine.generate_financial_statement_b01(db, workspace_id)
    return {"status": "success", "data": report}


@router.get("/workspaces/{workspace_id}/finance/tt58/reports/b02")
def get_report_b02(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    report = tt58_engine.generate_financial_statement_b02(db, workspace_id)
    return {"status": "success", "data": report}


@router.get("/workspaces/{workspace_id}/finance/tt58/reports/b03")
def get_report_b03(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    report = tt58_engine.generate_financial_statement_b03(db, workspace_id)
    return {"status": "success", "data": report}


@router.get("/workspaces/{workspace_id}/finance/tt58/reports/f01")
def get_report_f01(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    report = tt58_engine.generate_tax_obligation_report_f01(db, workspace_id)
    return {"status": "success", "data": report}

