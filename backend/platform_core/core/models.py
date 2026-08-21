from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from db.base_class import Base
from core.snowflake import generate_snowflake_id

class WorkspaceDomain(Base):
    __tablename__ = "workspace_domains"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    subdomain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    site_type: Mapped[str] = mapped_column(String(50), default="landing", nullable=False) # landing, product, docs, portal
    environment: Mapped[str] = mapped_column(String(50), default="production", nullable=False) # production, staging
    deployment_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    navigation_group_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    site_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metadata_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending") # pending, active, failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NavigationGroup(Base):
    __tablename__ = "navigation_groups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    site_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False) # domain or slug
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class NavigationItem(Base):
    __tablename__ = "navigation_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    group_id: Mapped[int] = mapped_column(ForeignKey("navigation_groups.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False) # e.g. "/#features", "https://blog.example.com"
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    target: Mapped[str] = mapped_column(String(50), default="_self", nullable=False) # _self, _blank
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    children_jsonb: Mapped[Optional[list]] = mapped_column(JSONB, default=list, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    actor_type: Mapped[str] = mapped_column(String(50)) # user, system, agent
    actor_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(100))
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[int] = mapped_column(BigInteger, index=True)
    metadata_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FeatureFlag(Base):
    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint('workspace_id', 'key', name='uix_feature_flag_workspace_key'),
        # PostgreSQL treats NULL values as distinct in a composite unique constraint.
        # This partial index keeps global defaults unique while allowing each workspace
        # to override the same capability key.
        Index('uix_feature_flags_global_key', 'key', unique=True, postgresql_where=text('workspace_id IS NULL')),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workspaces.id"), nullable=True, index=True)
    key: Mapped[str] = mapped_column(String(100), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RuntimeHeartbeat(Base):
    __tablename__ = "runtime_heartbeats"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    component: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
