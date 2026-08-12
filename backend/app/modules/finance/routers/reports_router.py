from fastapi import APIRouter, Depends

from app.db.models import WorkspaceMember
from app.modules.finance.auth import require_finance_access

router = APIRouter()


@router.get("")
def list_reports(workspace_id: int, member: WorkspaceMember = Depends(require_finance_access)):
    return {"reports": [], "message": "TT58 Mode 1 book reports are available through /books/templates"}
