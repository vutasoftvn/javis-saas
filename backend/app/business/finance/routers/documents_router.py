from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.business.finance.auth import require_finance_access
from app.business.finance.models import AccountingDocument

router = APIRouter()


@router.get("")
def list_documents(workspace_id: int, member: WorkspaceMember = Depends(require_finance_access), db: Session = Depends(get_db)):
    rows = db.query(AccountingDocument).filter(AccountingDocument.workspace_id == workspace_id).order_by(AccountingDocument.document_date.desc()).all()
    return {"documents": [{"id": str(row.id), "document_no": row.document_no, "date": row.document_date.isoformat(), "type": row.document_type, "status": row.status, "artifact_id": str(row.artifact_id) if row.artifact_id else None} for row in rows]}
