from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.core.auth import get_current_workspace_member, get_current_user
from app.db.models import User, WorkspaceMember, Brain
from app.db.repositories.vault_repo import VaultRepository
from app.integrations.s3_client import get_object, generate_presigned_download_url, generate_presigned_upload_url
from app.modules.vault.graph_service import build_graph

router = APIRouter()

def get_vault_repo(
    brain_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
) -> VaultRepository:
    # QUAN TRỌNG: brain_id đến từ path, workspace_id chỉ chứng minh user là thành viên
    # CỦA workspace_id đó - không chứng minh brain_id thuộc workspace_id. Không có bước
    # này, user A có thể đọc/ghi vault của brain thuộc workspace khác chỉ bằng cách tự
    # khai workspace_id=<workspace của mình> trong query string (đã kiểm chứng thực tế).
    brain = db.query(Brain).filter(Brain.id == brain_id).first()
    if not brain or brain.workspace_id != member.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brain not found")
    return VaultRepository(db=db, user_id=member.user_id, brain_id=brain_id, role=member.role)


@router.get("/{brain_id}/documents")
def list_vault_documents(
    brain_id: int,
    workspace_id: int,
    repo: VaultRepository = Depends(get_vault_repo)
):
    from app.db.models import VaultDocument
    docs = repo.db.query(VaultDocument).filter(
        VaultDocument.brain_id == brain_id,
        VaultDocument.status == "active"
    ).all()
    
    return {
        "documents": [
            {
                "id": str(d.id),
                "path": d.path,
                "kind": d.kind,
                "current_revision_id": str(d.current_revision_id) if d.current_revision_id else None,
                "updated_at": d.updated_at.isoformat()
            } for d in docs
        ]
    }

@router.get("/{brain_id}/documents/{path:path}")
def read_vault_document(
    path: str,
    brain_id: int,
    workspace_id: int,
    repo: VaultRepository = Depends(get_vault_repo)
):
    doc = repo.get_document(path)
    if not doc or not doc.current_revision_id:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # We would typically join VaultRevision here, but to keep it simple we query the content from S3 directly
    # In a full implementation we would get the revision to get the object_key
    # Assuming object_key is known or queried:
    rev = doc.current_revision_id # this is just the ID
    from app.db.models import VaultRevision
    revision = repo.db.query(VaultRevision).filter(VaultRevision.id == rev).first()
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")
    
    content = get_object(revision.object_key)
    return {
        "id": str(doc.id),
        "path": doc.path,
        "kind": doc.kind,
        "current_revision_id": str(revision.id),
        "content": content.decode("utf-8")
    }

@router.post("/{brain_id}/documents/{path:path}/restore")
def restore_vault_document_revision(
    path: str,
    brain_id: int,
    workspace_id: int,
    revision_id: int = Form(...),
    repo: VaultRepository = Depends(get_vault_repo)
):
    # QUAN TRỌNG: route này PHẢI đứng trước route POST "/{brain_id}/documents/{path:path}"
    # bên dưới. Converter {path:path} khớp tham lam cả dấu "/", nên nếu route ghi document
    # được đăng ký trước thì mọi request .../restore sẽ bị nó nuốt mất (path sẽ thành
    # "wiki/hello.md/restore"), gây 422 thiếu field "content" - đã tái hiện lỗi này thực tế.
    #
    # Khôi phục = tạo một revision MỚI có nội dung của revision cũ, không sửa/xóa
    # revision cũ - đúng nguyên tắc vault_revisions immutable (§5.3).
    from app.db.models import VaultRevision

    doc = repo.get_document(path)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    target_revision = repo.db.query(VaultRevision).filter(
        VaultRevision.id == revision_id,
        VaultRevision.document_id == doc.id
    ).first()
    if not target_revision:
        raise HTTPException(status_code=404, detail="Revision not found")

    content = get_object(target_revision.object_key)
    rev = repo.update_document(path, doc.kind, content, base_revision_id=doc.current_revision_id)

    return {
        "status": "success",
        "revision_id": str(rev.id),
        "restored_from": str(revision_id)
    }

@router.post("/{brain_id}/documents/{path:path}")
def write_vault_document(
    path: str,
    brain_id: int,
    workspace_id: int,
    content: str = Form(...),
    kind: str = Form("wiki"),
    base_revision_id: Optional[int] = Form(None),
    repo: VaultRepository = Depends(get_vault_repo)
):
    # Có thể raise 409 VAULT_REVISION_CONFLICT. Ghi S3 đã xảy ra bên trong
    # repo.update_document() trước khi commit DB - không gọi lại put_object ở đây.
    content_bytes = content.encode("utf-8")
    rev = repo.update_document(path, kind, content_bytes, base_revision_id)

    return {
        "status": "success",
        "revision_id": str(rev.id)
    }

@router.get("/{brain_id}/attachments/{object_key:path}/presigned-url")
def get_attachment_presigned_url(
    object_key: str,
    brain_id: int,
    workspace_id: int,
    repo: VaultRepository = Depends(get_vault_repo)
):
    # Note: RBAC is checked by getting repo (viewer role)
    url = generate_presigned_download_url(object_key)
    return {"url": url}


@router.get("/{brain_id}/graph")
def get_vault_graph(
    brain_id: int,
    workspace_id: int,
    repo: VaultRepository = Depends(get_vault_repo)
):
    return build_graph(repo.db, brain_id)
