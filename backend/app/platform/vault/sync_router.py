from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.db.models import Brain, VaultDocument, WorkspaceMember
from app.db.session import get_db

router = APIRouter()


@router.get("")
def sync(
    workspace_id: str = Query(...),
    cursor: Optional[str] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    # Cursor tối giản cho Phase 1: chỉ đồng bộ vault_documents. Các domain khác
    # (chat/tasks/strategy...) sẽ được thêm key riêng vào cùng response này ở
    # phase sau - không đổi shape response hiện có, chỉ mở rộng thêm.
    since = datetime.fromisoformat(cursor) if cursor else datetime.fromtimestamp(0, tz=timezone.utc)

    # Chỉ đồng bộ brain thuộc đúng workspace user đã được xác thực là thành viên -
    # không tin brain_id do client tự khai (cùng nguyên tắc đã sửa ở vault.py).
    brain_ids = [
        b.id for b in db.query(Brain.id).filter(Brain.workspace_id == member.workspace_id).all()
    ]

    docs = (
        db.query(VaultDocument)
        .filter(VaultDocument.brain_id.in_(brain_ids), VaultDocument.updated_at > since)
        .order_by(VaultDocument.updated_at.asc())
        .all()
    )

    new_cursor = max((d.updated_at for d in docs), default=since)

    return {
        "vault_documents": [
            {
                "id": str(d.id),
                "brain_id": str(d.brain_id),
                "path": d.path,
                "kind": d.kind,
                "current_revision_id": str(d.current_revision_id) if d.current_revision_id else None,
                "status": d.status,
                "updated_at": d.updated_at.isoformat(),
            }
            for d in docs
        ],
        "cursor": new_cursor.isoformat(),
    }
