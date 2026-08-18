from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.db.models import VaultDocument, VaultRevision, AuditLog, Brain
from app.integrations.storage.s3_client import put_object
import hashlib
from typing import Optional

ROLE_LEVELS = {"owner": 4, "admin": 3, "editor": 2, "member": 2, "viewer": 1}


def check_permission(role: str, required_level: str):
    if ROLE_LEVELS.get(role, 0) < ROLE_LEVELS.get(required_level, 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Require at least {required_level} role"
        )

class VaultRepository:
    def __init__(self, db: Session, user_id: int, brain_id: int, role: str):
        self.db = db
        self.user_id = user_id
        self.brain_id = brain_id
        self.role = role

    def get_document(self, path: str) -> Optional[VaultDocument]:
        check_permission(self.role, "viewer")
        return self.db.query(VaultDocument).filter(
            VaultDocument.brain_id == self.brain_id,
            VaultDocument.path == path
        ).first()

    def update_document(self, path: str, kind: str, content: bytes, base_revision_id: Optional[int] = None) -> VaultRevision:
        check_permission(self.role, "editor")
        
        doc = self.get_document(path)

        # Bắt buộc client phải biết đúng revision hiện tại mới được ghi đè. Nếu doc đã
        # tồn tại mà base_revision_id thiếu hoặc lệch (kể cả None), coi là conflict -
        # tránh trường hợp client "quên" gửi base_revision_id ghi đè âm thầm bản của
        # người khác (đã tái hiện lỗi này thực tế: gọi update không kèm base_revision_id
        # trên document đã có sẽ overwrite không cảnh báo).
        if doc:
            if doc.current_revision_id != base_revision_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="VAULT_REVISION_CONFLICT"
                )
        elif base_revision_id is not None:
            # Client nghĩ document đã tồn tại (gửi base_revision_id) nhưng chưa có.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="VAULT_REVISION_CONFLICT"
            )

        if not doc:
            doc = VaultDocument(brain_id=self.brain_id, path=path, kind=kind)
            self.db.add(doc)
            self.db.flush()

        sha256_hash = hashlib.sha256(content).hexdigest()
        object_key = f"{self.brain_id}/{path}/{sha256_hash}"

        # Ghi S3 TRƯỚC khi commit DB. object_key theo sha256 nên idempotent nếu phải
        # retry; nếu S3 lỗi thì hàm raise trước khi tới db.commit() -> transaction chưa
        # commit sẽ tự rollback khi session đóng, không để lại revision "ma" trỏ vào
        # object không tồn tại (đã tái hiện lỗi NoSuchBucket gây đúng tình huống này).
        put_object(object_key, content)

        # Create Revision
        rev = VaultRevision(
            document_id=doc.id,
            object_key=object_key,
            sha256=sha256_hash,
            size_bytes=len(content),
            created_by=self.user_id
        )
        self.db.add(rev)
        self.db.flush()

        doc.current_revision_id = rev.id

        # Audit Log. metadata_jsonb must carry workspace_id - it's the field
        # platform/router.py::list_audit_events filters on to keep audit trails
        # tenant-scoped; an entry without it is invisible to the correct
        # workspace's audit view (and was previously only surfaced via a leaky
        # actor-membership fallback that has since been removed).
        workspace_id = self.db.query(Brain.workspace_id).filter(Brain.id == self.brain_id).scalar()
        audit = AuditLog(
            actor_type="user",
            actor_id=self.user_id,
            action="update_vault_document",
            target_type="vault_document",
            target_id=doc.id,
            metadata_jsonb={
                "path": path,
                "revision_id": str(rev.id),
                "workspace_id": str(workspace_id) if workspace_id else None,
            }
        )
        self.db.add(audit)

        # Create Chunking Job for RAG
        from app.db.models import ChunkingJob
        chunk_job = ChunkingJob(
            document_id=doc.id,
            revision_id=rev.id
        )
        self.db.add(chunk_job)

        self.db.commit()
        self.db.refresh(doc)
        self.db.refresh(rev)

        return rev
