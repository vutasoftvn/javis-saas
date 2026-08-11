from datetime import datetime
import uuid
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import AuditLog
from app.core.events import publish_event


def write_audit_log(
    db: Session,
    actor_type: str,
    actor_id: uuid.UUID,
    action: str,
    target_type: str,
    target_id: uuid.UUID,
    metadata_jsonb: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Ghi nhận nhật ký kiểm toán (Audit Log) cho các hành động trọng yếu.
    
    Tuân thủ nguyên tắc 'every consequential action must be audited' (§39, §53, §120).
    """
    log_entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_jsonb=metadata_jsonb,
        created_at=datetime.utcnow(),
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    # Broadcast real-time audit event if workspace_id is provided
    ws_id_str = (metadata_jsonb or {}).get("workspace_id")
    if ws_id_str:
        try:
            ws_id = uuid.UUID(ws_id_str)
            publish_event(
                event_type=f"audit.{action}",
                workspace_id=ws_id,
                actor_id=actor_id,
                payload={
                    "audit_id": str(log_entry.id),
                    "action": action,
                    "target_type": target_type,
                    "target_id": str(target_id),
                    "metadata": metadata_jsonb,
                }
            )
        except Exception:
            pass

    return log_entry
