from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import BigInteger, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from cosa_core.db.base import Base
from cosa_core.snowflake import generate_snowflake_id
from cosa_core.events import publish_event


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    actor_type: Mapped[str] = mapped_column(String(50))
    actor_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(100))
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[int] = mapped_column(BigInteger, index=True)
    metadata_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def write_audit_log(
    db: Session,
    actor_type: str,
    actor_id: int,
    action: str,
    target_type: str,
    target_id: int,
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
            ws_id = int(ws_id_str)
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
