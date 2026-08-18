from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.db.models import WorkspaceMember
from app.business.finance.models import AccountingProfile
from app.business.finance.auth import require_finance_access
from app.business.finance.regulations.tt58_2026.registry import get_book_templates

router = APIRouter()


@router.get("/templates")
def list_book_templates(
    workspace_id: int,
    mode: Optional[str] = None,
    member: WorkspaceMember = Depends(require_finance_access),
    db: Session = Depends(get_db),
):
    if not mode:
        profile = db.query(AccountingProfile).filter(AccountingProfile.workspace_id == workspace_id).first()
        mode = profile.mode if profile and profile.mode else "TT58_MODE_1"
    return {"templates": get_book_templates(mode)}
