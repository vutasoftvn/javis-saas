from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from db.base_class import Base
from core.snowflake import generate_snowflake_id

class StrategyCanvas(Base):
    # Đổi tên từ "strategy_profiles" (Phase 2B cũ) sang "strategy_canvases" khi triển
    # khai Strategic Canvas 1-1-3 - cùng một khái niệm (1 container chiến lược theo
    # workspace/brain), chỉ bổ sung name/description/created_by thay vì tạo bảng song
    # song. FK cũ (BscScorecard.strategy_profile_id) vẫn giữ nguyên tên cột, Postgres
    # tự cập nhật theo bảng đổi tên.
    __tablename__ = "strategy_canvases"
    __table_args__ = {"schema": "strategy"}
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("knowledge.brains.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("core.users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class StrategyRevision(Base):
    # Immutable revision theo Canvas (Strategic Canvas 1-1-3 §3.1). Không có khái niệm
    # tương đương nào ở Phase 2B cũ - strategy_canvases/context_packs trước đây chỉ có
    # 1 status phẳng, không có revision_no/lifecycle/parent_revision_id.
    __tablename__ = "strategy_revisions"
    __table_args__ = (
        UniqueConstraint('canvas_id', 'revision_no', name='uix_strategy_revision_canvas_no'),
        {"schema": "strategy"},
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    canvas_id: Mapped[int] = mapped_column(ForeignKey("strategy.strategy_canvases.id"), index=True)
    revision_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, in_review, approved, changes_requested, superseded, archived
    parent_revision_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy.strategy_revisions.id", use_alter=True), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("core.users.id"))
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("core.users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    stale_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StrategyFoundation(Base):
    # 1 Vision, 1 Mission theo revision (§4.1). Không tồn tại ở Phase 2B cũ.
    __tablename__ = "strategy_foundations"
    __table_args__ = {"schema": "strategy"}
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    strategy_revision_id: Mapped[int] = mapped_column(ForeignKey("strategy.strategy_revisions.id"), unique=True, index=True)
    vision: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mission: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, approved
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CoreValue(Base):
    # Đúng 3 slot/foundation (§4.1) - unique(foundation_id, slot_no) + CHECK slot_no
    # 1-3 ở migration đảm bảo không tạo được value thứ 4.
    __tablename__ = "core_values"
    __table_args__ = (
        UniqueConstraint('foundation_id', 'slot_no', name='uix_core_value_foundation_slot'),
        {"schema": "strategy"},
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    foundation_id: Mapped[int] = mapped_column(ForeignKey("strategy.strategy_foundations.id", ondelete="CASCADE"), index=True)
    slot_no: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    decision_rule: Mapped[str] = mapped_column(Text)
