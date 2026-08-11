from datetime import datetime
import hashlib
import re
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.modules.vault.models import Brain, KnowledgeObject, KnowledgeRelation
from app.core.audit import write_audit_log
from app.core.events import publish_event

WIKILINK_PATTERN = re.compile(r'\[\[(.*?)\]\]')


def create_knowledge_object(
    db: Session,
    workspace_id: int,
    brain_id: int,
    title: str,
    content: Optional[str] = None,
    object_type: str = "note",
    status: str = "capture",
    generated_by: Optional[int] = None,
    confidence: float = 1.0,
    vault_document_id: Optional[int] = None,
) -> KnowledgeObject:
    source_hash = hashlib.sha256((content or "").encode('utf-8')).hexdigest() if content else None

    obj = KnowledgeObject(
        workspace_id=workspace_id,
        brain_id=brain_id,
        vault_document_id=vault_document_id,
        title=title,
        content=content,
        object_type=object_type,
        status=status,
        source_hash=source_hash,
        generated_by=generated_by,
        confidence=confidence,
        created_at=datetime.utcnow(),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    # Tự động phân tích các [[wikilinks]] để tạo quan hệ đồ thị tri thức
    if content:
        parse_wikilinks_and_create_relations(db=db, from_object=obj)

    return obj


def parse_wikilinks_and_create_relations(
    db: Session,
    from_object: KnowledgeObject,
) -> List[KnowledgeRelation]:
    if not from_object.content:
        return []

    targets = WIKILINK_PATTERN.findall(from_object.content)
    created_relations = []

    for target_title in set(targets):
        clean_title = target_title.strip()
        if not clean_title:
            continue

        target_obj = db.query(KnowledgeObject).filter(
            KnowledgeObject.brain_id == from_object.brain_id,
            KnowledgeObject.title.ilike(clean_title)
        ).first()

        if target_obj and target_obj.id != from_object.id:
            existing = db.query(KnowledgeRelation).filter(
                KnowledgeRelation.from_object_id == from_object.id,
                KnowledgeRelation.to_object_id == target_obj.id
            ).first()

            if not existing:
                relation = KnowledgeRelation(
                    from_object_id=from_object.id,
                    to_object_id=target_obj.id,
                    relation_type="RELATED_TO",
                    created_at=datetime.utcnow(),
                )
                db.add(relation)
                created_relations.append(relation)

    if created_relations:
        db.commit()

    return created_relations


def list_knowledge_objects(
    db: Session,
    brain_id: int,
    workspace_id: int,
    object_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[KnowledgeObject]:
    query = db.query(KnowledgeObject).filter(
        KnowledgeObject.brain_id == brain_id,
        KnowledgeObject.workspace_id == workspace_id,
    )
    if object_type:
        query = query.filter(KnowledgeObject.object_type == object_type)
    if status:
        query = query.filter(KnowledgeObject.status == status)

    return query.order_by(KnowledgeObject.created_at.desc()).offset(offset).limit(limit).all()


def get_knowledge_object(
    db: Session,
    object_id: int,
    brain_id: int,
    workspace_id: int,
) -> Optional[KnowledgeObject]:
    return db.query(KnowledgeObject).filter(
        KnowledgeObject.id == object_id,
        KnowledgeObject.brain_id == brain_id,
        KnowledgeObject.workspace_id == workspace_id,
    ).first()


def get_backlinks(
    db: Session,
    object_id: int,
    brain_id: int,
    workspace_id: int,
) -> List[Dict[str, Any]]:
    # Đọc tất cả các liên kết trỏ tới object_id này
    relations = db.query(KnowledgeRelation, KnowledgeObject).join(
        KnowledgeObject, KnowledgeRelation.from_object_id == KnowledgeObject.id
    ).filter(
        KnowledgeRelation.to_object_id == object_id,
        KnowledgeObject.workspace_id == workspace_id,
        KnowledgeObject.brain_id == brain_id,
    ).all()

    return [
        {
            "relation_id": str(rel.id),
            "relation_type": rel.relation_type,
            "source_object_id": str(src.id),
            "source_title": src.title,
            "source_type": src.object_type,
            "created_at": rel.created_at.isoformat(),
        }
        for rel, src in relations
    ]


def promote_knowledge_object(
    db: Session,
    object_id: int,
    brain_id: int,
    workspace_id: int,
    user_id: int,
    target_status: str = "approved",
) -> KnowledgeObject:
    obj = get_knowledge_object(db=db, object_id=object_id, brain_id=brain_id, workspace_id=workspace_id)
    if not obj:
        raise ValueError("Knowledge object not found or access denied")

    previous_status = obj.status
    obj.status = target_status
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)

    # Ghi nhận audit log bắt buộc (§65, §120)
    write_audit_log(
        db=db,
        actor_type="user",
        actor_id=user_id,
        action="knowledge.promote",
        target_type="knowledge_object",
        target_id=obj.id,
        metadata_jsonb={
            "workspace_id": str(workspace_id),
            "brain_id": str(brain_id),
            "title": obj.title,
            "previous_status": previous_status,
            "new_status": target_status,
        }
    )

    publish_event(
        event_type="knowledge.promoted",
        workspace_id=workspace_id,
        actor_id=user_id,
        payload={"object_id": str(obj.id), "title": obj.title, "status": target_status}
    )

    return obj
