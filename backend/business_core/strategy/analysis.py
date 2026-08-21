from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from db.base_class import Base
from core.snowflake import generate_snowflake_id

class StrategyAnalysis(Base):
    __tablename__ = "strategy_analyses"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    portfolio_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    context_pack_id: Mapped[int] = mapped_column(ForeignKey("context_packs.id"), index=True)
    kind: Mapped[str] = mapped_column(String(50)) # PESTEL, SWOT, TOWS
    status: Mapped[str] = mapped_column(String(50), default="draft")
    input_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    output_revision_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PestelItem(Base):
    __tablename__ = "pestel_items"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    portfolio_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("strategy_analyses.id"), index=True)
    factor: Mapped[str] = mapped_column(String(50))
    statement: Mapped[str] = mapped_column(Text)
    impact: Mapped[str] = mapped_column(String(50))
    horizon: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[str] = mapped_column(String(50))
    evidence_status: Mapped[str] = mapped_column(String(50))

class SwotItem(Base):
    __tablename__ = "swot_items"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    portfolio_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    analysis_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy_analyses.id"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(50)) # STRENGTH | WEAKNESS | OPPORTUNITY | THREAT
    statement: Mapped[str] = mapped_column(Text)
    impact: Mapped[str] = mapped_column(String(50), default="medium")
    likelihood: Mapped[str] = mapped_column(String(50), default="medium")
    confidence: Mapped[str] = mapped_column(String(50), default="medium")
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_status: Mapped[str] = mapped_column(String(50), default="unverified")
    
    # Evidence refs bắt buộc cho Strength & Weakness
    evidence_refs: Mapped[dict] = mapped_column(JSONB, default=list) # List[int]: evidence_ids
    pestel_signal_ref: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TowsOption(Base):
    __tablename__ = "tows_options"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    portfolio_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    analysis_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy_analyses.id"), nullable=True, index=True)
    quadrant: Mapped[str] = mapped_column(String(50)) # SO | WO | ST | WT
    title: Mapped[str] = mapped_column(String(255))
    tradeoffs: Mapped[str] = mapped_column(Text, default="")
    expected_impact: Mapped[str] = mapped_column(String(50), default="high")
    confidence: Mapped[str] = mapped_column(String(50), default="medium")
    status: Mapped[str] = mapped_column(String(50), default="draft")
    
    linked_strength_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    linked_weakness_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    linked_opportunity_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    linked_threat_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    
    resulting_hypothesis_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    tactics_12wy: Mapped[dict] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PestelSignal(Base):
    """Tín hiệu vĩ mô Living PESTEL theo chuẩn COSA Stage-Aware."""
    __tablename__ = "pestel_signals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    dimension: Mapped[str] = mapped_column(String(50), default="economic", index=True)
    signal_title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signal_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pestel_category: Mapped[str] = mapped_column(String(50), default="ECONOMIC")  # POLITICAL, ECONOMIC, SOCIAL, TECHNOLOGICAL, ENVIRONMENTAL, LEGAL
    impact_level: Mapped[str] = mapped_column(String(50), default="medium")  # high | medium | low
    magnitude: Mapped[str] = mapped_column(String(50), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    time_horizon: Mapped[str] = mapped_column(String(50), default="medium_term")
    is_material_change: Mapped[bool] = mapped_column(Boolean, default=False)
    resulting_hypothesis_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    stage_captured: Mapped[str] = mapped_column(String(50), default="S0_EXPLORE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AnalysisImport(Base):
    __tablename__ = "analysis_imports"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    strategy_revision_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy_revisions.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_input: Mapped[str] = mapped_column(Text)
    parsed_json: Mapped[dict] = mapped_column(JSONB)
    schema_version: Mapped[str] = mapped_column(String(50), default="1.0")
    imported_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# ==========================================
# Retrieval and AI Router (Phase 3) & Prompt Templates
# ==========================================
