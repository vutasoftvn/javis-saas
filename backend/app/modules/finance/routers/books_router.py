from fastapi import APIRouter, Depends

from app.db.models import WorkspaceMember
from app.modules.finance.auth import require_finance_access
from app.modules.finance.regulations.tt58_2026.registry import get_book_templates

router = APIRouter()


@router.get("/templates")
def list_book_templates(workspace_id: int, mode: str = "TT58_MODE_1", member: WorkspaceMember = Depends(require_finance_access)):
    return {"templates": get_book_templates(mode)}
