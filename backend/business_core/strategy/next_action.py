from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from db.base_class import Base
from core.snowflake import generate_snowflake_id

class NextActionCandidate(Base):
    """Ứng viên hành động tiếp theo tốt nhất cho CEO / Founder (Spec §37)."""
    __tablename__ = "next_action_candidates"
    __table_args__ = {"schema": "strategy"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy.projects.id", ondelete="CASCADE"), nullable=True, index=True)
    portfolio_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy.portfolios.id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="GOVERNANCE_DECISION")  # STAGE_GATE_REVIEW, WEEKLY_MISSION, PESTEL_MITIGATION, GOVERNANCE_DECISION, STRATEGIC_ALIGNMENT
    urgency_score: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0 - 1.0
    impact_score: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0 - 1.0
    effort_score: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0 - 1.0
    r0_score: Mapped[float] = mapped_column(Float, default=0.5)  # Deterministic weighted formula §37
    status: Mapped[str] = mapped_column(String(50), default="proposed")  # proposed, accepted, dismissed, executed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class NextActionRanking(Base):
    """Kết quả xếp hạng danh sách Next Best Action theo các vòng R0, R1, R2."""
    __tablename__ = "next_action_rankings"
    __table_args__ = {"schema": "strategy"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("strategy.next_action_candidates.id", ondelete="CASCADE"), index=True)
    ranking_round: Mapped[str] = mapped_column(String(50), default="R0_DETERMINISTIC")  # R0_DETERMINISTIC, R1_RULES, R2_AI_TERRA
    rank_position: Mapped[int] = mapped_column(Integer, default=1)
    composite_score: Mapped[float] = mapped_column(Float, default=0.5)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==========================================
# mCOSA V12 — Living PESTEL & Model Audit (Sprint 10 Spec §48 & V12.7)
# ==========================================
