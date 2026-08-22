from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from db.base_class import Base
from core.snowflake import generate_snowflake_id

class Portfolio(Base):
    """Mô hình Portfolio - Danh mục quản lý nhiều dự án chiến lược (§21–23)."""
    __tablename__ = "portfolios"
    __table_args__ = {"schema": "strategy"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    brain_id: Mapped[Optional[int]] = mapped_column(ForeignKey("knowledge.brains.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    strategic_focus: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, archived, draft
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PortfolioProject(Base):
    """Liên kết Dự án vào Danh mục với phân bổ năng lực & độ ưu tiên chiến lược (§23)."""
    __tablename__ = "portfolio_projects"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "project_id", name="uix_portfolio_project"),
        {"schema": "strategy"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("strategy.portfolios.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id", ondelete="CASCADE"), index=True)
    strategic_priority: Mapped[str] = mapped_column(String(50), default="core")  # core, growth, experimental, maintenance
    capacity_allocation: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 - 100.0%
    founder_attention_hours: Mapped[float] = mapped_column(Float, default=0.0)  # hours/week
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PortfolioSynergy(Base):
    """Cộng hưởng giá trị giữa các dự án trong Danh mục (Spec §25)."""
    __tablename__ = "portfolio_synergies"
    __table_args__ = {"schema": "strategy"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("strategy.portfolios.id", ondelete="CASCADE"), index=True)
    source_project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id", ondelete="CASCADE"), index=True)
    target_project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id", ondelete="CASCADE"), index=True)
    synergy_type: Mapped[str] = mapped_column(String(50), default="SHARED_CAPABILITY")  # REVENUE, COST_SAVING, SHARED_CAPABILITY, DATA_NETWORK
    description: Mapped[str] = mapped_column(Text)
    estimated_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="identified")  # identified, active, realized
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PortfolioDependency(Base):
    """Quan hệ phụ thuộc giữa các dự án trong Danh mục (Spec §26)."""
    __tablename__ = "portfolio_dependencies"
    __table_args__ = {"schema": "strategy"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("strategy.portfolios.id", ondelete="CASCADE"), index=True)
    predecessor_project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id", ondelete="CASCADE"), index=True)
    successor_project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id", ondelete="CASCADE"), index=True)
    dependency_type: Mapped[str] = mapped_column(String(50), default="BLOCKS")  # BLOCKS, ENABLES, REQUIRES_MILESTONE
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PortfolioOption(Base):
    """Tùy chọn chiến lược cấp Danh mục (Portfolio Strategic Options - Spec §27)."""
    __tablename__ = "portfolio_options"
    __table_args__ = {"schema": "strategy"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("strategy.portfolios.id", ondelete="CASCADE"), index=True)
    tows_option_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy.tows_options.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    strategic_fit_score: Mapped[float] = mapped_column(Float, default=0.8)  # 0.0 - 1.0
    feasibility_score: Mapped[float] = mapped_column(Float, default=0.7)  # 0.0 - 1.0
    risk_level: Mapped[str] = mapped_column(String(50), default="MEDIUM")  # LOW, MEDIUM, HIGH
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, under_review, selected, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==========================================
# mCOSA V12 — Portfolio Cycles, WIP Limit & Capacity (Sprint 8)
# ==========================================

class PortfolioCycle(Base):
    """Chu kỳ 12 tuần cấp Danh mục (Portfolio 12WY Cycle - Spec §28–30)."""
    __tablename__ = "portfolio_cycles"
    __table_args__ = {"schema": "strategy"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("strategy.portfolios.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, active, completed, archived
    start_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    active_project_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CapacityAllocation(Base):
    """Phân bổ công suất đội ngũ cho các dự án trong chu kỳ danh mục."""
    __tablename__ = "capacity_allocations"
    __table_args__ = {"schema": "strategy"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    portfolio_cycle_id: Mapped[int] = mapped_column(ForeignKey("strategy.portfolio_cycles.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id", ondelete="CASCADE"), index=True)
    allocated_percentage: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 - 100.0%
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class FounderAttentionAllocation(Base):
    """Phân bổ thời gian tập trung hàng tuần của Founder cho các dự án."""
    __tablename__ = "founder_attention_allocations"
    __table_args__ = {"schema": "strategy"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    portfolio_cycle_id: Mapped[int] = mapped_column(ForeignKey("strategy.portfolio_cycles.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id", ondelete="CASCADE"), index=True)
    allocated_hours_per_week: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==========================================
# mCOSA V12 — Next Best Action Engine (Sprint 9 Spec §37 & V12.6)
# ==========================================
