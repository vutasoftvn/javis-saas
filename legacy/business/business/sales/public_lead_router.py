from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from db.session import get_db
from business.sales.revenue_engine_service import ingest_public_lead

router = APIRouter()


class PublicLeadSubmission(BaseModel):
    name: str = Field(..., description="Họ và tên người liên hệ")
    email: Optional[str] = Field(None, description="Địa chỉ Email")
    phone: Optional[str] = Field(None, description="Số điện thoại")
    company: Optional[str] = Field(None, description="Tên công ty / Doanh nghiệp")
    message: Optional[str] = Field(None, description="Nhu cầu hoặc lời nhắn")
    utm_source: Optional[str] = Field("landing_page", description="Nguồn UTM")
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


@router.post("/public/landing-pages/{slug}/submit-lead")
def submit_public_lead(
    slug: str,
    payload: PublicLeadSubmission,
    db: Session = Depends(get_db),
):
    """Tiếp nhận Lead gửi từ Landing Page công khai."""
    try:
        res = ingest_public_lead(
            db=db,
            slug=slug,
            payload=payload.dict(exclude_unset=True),
        )
        return res
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi tiếp nhận thông tin: {str(exc)}",
        )
