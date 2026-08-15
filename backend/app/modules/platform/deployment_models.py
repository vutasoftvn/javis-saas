from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id


class Deployment(Base):
    """Deployment record for modular landing applications and services on VPS infrastructure."""
    __tablename__ = "deployments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    domain_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workspace_domains.id"), nullable=True, index=True)

    provider: Mapped[str] = mapped_column(String(50), default="hostinger", nullable=False)
    vps_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    compose_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Status: pending, deploying, running, failed, stopped
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    logs_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    last_deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
