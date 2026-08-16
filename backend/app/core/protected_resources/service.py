"""Service layer for Protected Resources lifecycle management (Revisions, Reset, Audit)."""

from datetime import datetime
import hashlib
import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.protected_resources.models import ProtectedResource, ProtectedResourceRevision
from app.core.snowflake import generate_snowflake_id
from app.modules.platform.models import AuditLog


def _calculate_checksum(content: dict) -> str:
    serialized = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def get_or_create_resource(
    db: Session,
    workspace_id: int,
    resource_type: str,
    resource_key: str,
    default_content: Optional[dict] = None,
    resettable: bool = True,
) -> ProtectedResource:
    """Find or initialize a ProtectedResource row with revision 0 (bundled default)."""
    resource = (
        db.query(ProtectedResource)
        .filter(
            ProtectedResource.workspace_id == workspace_id,
            ProtectedResource.resource_type == resource_type,
            ProtectedResource.resource_key == resource_key,
        )
        .first()
    )
    if resource is not None:
        return resource

    resource = ProtectedResource(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_key=resource_key,
        active_revision_no=0,
        editable_by=["admin"],
        resettable=resettable,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(resource)

    # Revision 0 represents immutable default
    default_body = default_content if default_content is not None else {}
    rev0 = ProtectedResourceRevision(
        id=generate_snowflake_id(),
        resource_id=resource.id,
        revision_no=0,
        content_jsonb=default_body,
        is_default=True,
        status="ACTIVE",
        created_by=None,
        checksum=_calculate_checksum(default_body),
        created_at=datetime.utcnow(),
    )
    db.add(rev0)
    db.commit()
    db.refresh(resource)
    return resource


def get_effective(
    db: Session,
    workspace_id: int,
    resource_type: str,
    resource_key: str,
    default_content: Optional[dict] = None,
) -> dict:
    """Return effective content for a protected resource."""
    resource = (
        db.query(ProtectedResource)
        .filter(
            ProtectedResource.workspace_id == workspace_id,
            ProtectedResource.resource_type == resource_type,
            ProtectedResource.resource_key == resource_key,
        )
        .first()
    )
    if not resource:
        return default_content if default_content is not None else {}

    target_rev_no = resource.active_revision_no
    revision = (
        db.query(ProtectedResourceRevision)
        .filter(
            ProtectedResourceRevision.resource_id == resource.id,
            ProtectedResourceRevision.revision_no == target_rev_no,
        )
        .first()
    )
    if revision:
        return revision.content_jsonb

    # Fallback to revision 0 if active revision not found
    rev0 = (
        db.query(ProtectedResourceRevision)
        .filter(
            ProtectedResourceRevision.resource_id == resource.id,
            ProtectedResourceRevision.revision_no == 0,
        )
        .first()
    )
    return rev0.content_jsonb if rev0 else (default_content or {})


def create_revision(
    db: Session,
    workspace_id: int,
    resource_type: str,
    resource_key: str,
    content: dict,
    actor_id: Optional[int] = None,
    default_content: Optional[dict] = None,
) -> ProtectedResourceRevision:
    """Create a new revision override and update active revision."""
    resource = get_or_create_resource(
        db,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_key=resource_key,
        default_content=default_content,
    )

    # Determine next revision number
    latest_rev = (
        db.query(ProtectedResourceRevision)
        .filter(ProtectedResourceRevision.resource_id == resource.id)
        .order_by(ProtectedResourceRevision.revision_no.desc())
        .first()
    )
    next_rev_no = (latest_rev.revision_no + 1) if latest_rev else 1

    revision = ProtectedResourceRevision(
        id=generate_snowflake_id(),
        resource_id=resource.id,
        revision_no=next_rev_no,
        content_jsonb=content,
        is_default=False,
        status="ACTIVE",
        created_by=actor_id,
        checksum=_calculate_checksum(content),
        created_at=datetime.utcnow(),
    )
    db.add(revision)

    resource.active_revision_no = next_rev_no
    resource.updated_at = datetime.utcnow()

    # Log to AuditLog
    audit_action = "CREATE_OVERRIDE" if next_rev_no == 1 else "UPDATE"
    audit = AuditLog(
        id=generate_snowflake_id(),
        actor_type="user" if actor_id else "system",
        actor_id=actor_id or 0,
        action=audit_action,
        target_type="protected_resource",
        target_id=resource.id,
        metadata_jsonb={
            "resource_type": resource_type,
            "resource_key": resource_key,
            "revision_no": next_rev_no,
        },
        created_at=datetime.utcnow(),
    )
    db.add(audit)
    db.commit()
    db.refresh(revision)
    return revision


def reset_to_default(
    db: Session,
    workspace_id: int,
    resource_type: str,
    resource_key: str,
    actor_id: Optional[int] = None,
) -> bool:
    """Reset resource to default revision (revision 0) and archive current overrides."""
    resource = (
        db.query(ProtectedResource)
        .filter(
            ProtectedResource.workspace_id == workspace_id,
            ProtectedResource.resource_type == resource_type,
            ProtectedResource.resource_key == resource_key,
        )
        .first()
    )
    if not resource or not resource.resettable:
        return False

    previous_active_no = resource.active_revision_no
    if previous_active_no == 0:
        return True  # Already on default

    # Archive active overrides
    overrides = (
        db.query(ProtectedResourceRevision)
        .filter(
            ProtectedResourceRevision.resource_id == resource.id,
            ProtectedResourceRevision.is_default == False,
            ProtectedResourceRevision.status == "ACTIVE",
        )
        .all()
    )
    for rev in overrides:
        rev.status = "ARCHIVED"

    resource.active_revision_no = 0
    resource.updated_at = datetime.utcnow()

    # Record AuditLog
    audit = AuditLog(
        id=generate_snowflake_id(),
        actor_type="user" if actor_id else "system",
        actor_id=actor_id or 0,
        action="RESET_TO_DEFAULT",
        target_type="protected_resource",
        target_id=resource.id,
        metadata_jsonb={
            "resource_type": resource_type,
            "resource_key": resource_key,
            "reset_from_revision_no": previous_active_no,
            "reset_to_revision_no": 0,
        },
        created_at=datetime.utcnow(),
    )
    db.add(audit)
    db.commit()
    return True


def list_revisions(
    db: Session,
    workspace_id: int,
    resource_type: str,
    resource_key: str,
) -> list[ProtectedResourceRevision]:
    """List all revisions for a protected resource sorted descending by revision_no."""
    resource = (
        db.query(ProtectedResource)
        .filter(
            ProtectedResource.workspace_id == workspace_id,
            ProtectedResource.resource_type == resource_type,
            ProtectedResource.resource_key == resource_key,
        )
        .first()
    )
    if not resource:
        return []

    return (
        db.query(ProtectedResourceRevision)
        .filter(ProtectedResourceRevision.resource_id == resource.id)
        .order_by(ProtectedResourceRevision.revision_no.desc())
        .all()
    )
