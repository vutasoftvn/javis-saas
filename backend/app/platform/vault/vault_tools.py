import logging
import hashlib
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.core.tool_registry import register
from app.db.models import Brain, WorkspaceMember, VaultDocument, VaultRevision, DocumentChunk, ChunkingJob
from app.db.repositories.vault_repo import VaultRepository
from app.core.snowflake import generate_snowflake_id

logger = logging.getLogger(__name__)


@register(
    "vault",
    "save_document",
    chat_schema={
        "description": (
            "Lưu tài liệu tri thức (Markdown .md) theo chuẩn Obsidian (kèm YAML Frontmatter và [[wikilinks]]) "
            "vào Knowledge Vault của workspace. Dùng để lưu kế hoạch, lộ trình, 12WY, spec, ADR hoặc báo cáo."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Đường dẫn file chuẩn theo thời gian và danh mục, ví dụ: "
                        "'projects/mid/roadmaps/2026-08-17_mid_roadmap-4-weeks_v1.0.md' hoặc "
                        "'strategy/12wy/2026-W34_12wy-commitments_v1.0.md' hoặc "
                        "'decisions/ADR-20260817-001_auth.md'."
                    ),
                },
                "content": {
                    "type": "string",
                    "description": "Nội dung Markdown đầy đủ, có YAML frontmatter metadata ở đầu và [[wikilinks]] liên kết.",
                },
                "kind": {
                    "type": "string",
                    "description": "Danh mục tài liệu: 'strategy', 'project', 'architecture', 'sop', 'report'. Mặc định 'strategy'.",
                },
            },
            "required": ["path", "content"],
        },
    },
)
def vault_save_document(
    db: Session,
    workspace_id: int,
    user_id: int,
    path: str,
    content: str,
    kind: str = "strategy",
) -> dict:
    """Lưu một tài liệu Markdown vào Knowledge Vault."""
    try:
        # Chuẩn hoá path: không có dấu gạch chéo đầu
        clean_path = path.strip().lstrip("/")
        if not clean_path:
            return {"ok": False, "error": "Đường dẫn tài liệu không hợp lệ."}

        brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
        if not brain:
            brain = Brain(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                name="Default Brain",
                slug="default",
            )
            db.add(brain)
            db.flush()

        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        ).first()
        role = member.role if member and member.role else "owner"

        repo = VaultRepository(db=db, user_id=user_id, brain_id=brain.id, role=role)
        existing = repo.get_document(clean_path)
        base_revision_id = existing.current_revision_id if existing else None

        revision = repo.update_document(
            path=clean_path,
            kind=kind,
            content=content.encode("utf-8"),
            base_revision_id=base_revision_id,
        )

        # Tạo chunk tức thì để Graph Service và Vector RAG có thể đọc ngay lập tức
        doc = repo.get_document(clean_path)
        if doc and revision:
            # Xoá chunk cũ nếu có
            db.query(DocumentChunk).filter(DocumentChunk.revision_id == revision.id).delete()
            chunk = DocumentChunk(
                id=generate_snowflake_id(),
                revision_id=revision.id,
                ordinal=0,
                text=content,
            )
            db.add(chunk)

            # Đẩy ChunkingJob cho worker băm nhỏ và nhúng embeddings
            job = ChunkingJob(
                id=generate_snowflake_id(),
                document_id=doc.id,
                revision_id=revision.id,
                status="queued",
            )
            db.add(job)
            db.commit()

        return {
            "ok": True,
            "path": clean_path,
            "revision_id": str(revision.id) if revision else None,
            "size_bytes": len(content.encode("utf-8")),
            "message": f"Đã lưu thành công tài liệu vào Knowledge Vault tại '{clean_path}'.",
        }
    except Exception as e:
        logger.exception("Lỗi khi lưu tài liệu vào Knowledge Vault")
        return {"ok": False, "error": f"Lỗi lưu tài liệu Vault: {str(e)}"}


@register(
    "vault",
    "list_documents",
    chat_schema={
        "description": "Tra cứu danh sách tài liệu tri thức Markdown hiện có trong Knowledge Vault của workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Từ khóa lọc đường dẫn hoặc tên tài liệu. Để trống để xem tất cả.",
                },
                "kind": {
                    "type": "string",
                    "description": "Lọc theo danh mục: 'strategy', 'project', 'architecture', 'sop', 'report'.",
                },
            },
            "required": [],
        },
    },
)
def vault_list_documents(
    db: Session,
    workspace_id: int,
    query: Optional[str] = None,
    kind: Optional[str] = None,
) -> dict:
    """Liệt kê các tài liệu trong Vault của workspace."""
    brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
    if not brain:
        return {"total": 0, "documents": []}

    q = db.query(VaultDocument).filter(
        VaultDocument.brain_id == brain.id,
        VaultDocument.status == "active",
    )
    if kind:
        q = q.filter(VaultDocument.kind == kind)
    if query and query.strip():
        q = q.filter(VaultDocument.path.ilike(f"%{query.strip()}%"))

    docs = q.order_by(VaultDocument.updated_at.desc()).limit(20).all()
    return {
        "total": len(docs),
        "documents": [
            {
                "id": str(d.id),
                "path": d.path,
                "kind": d.kind,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            }
            for d in docs
        ],
    }
