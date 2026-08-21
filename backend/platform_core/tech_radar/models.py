"""Technology Radar Model for COSA Operating System (Spec §104, §P5)."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base_class import Base
from db.snowflake_model import SnowflakeIDMixin


class TechnologyRadarItem(SnowflakeIDMixin, Base):
    """Technology Radar Item (Spec §104).
    
    Categories:
      Runtime, Orchestration, Memory, Browser, Security, Governance, Evaluation, Coding, Communication, Research.
    
    Status:
      ADOPT, TRIAL, ASSESS, WATCH, REJECT.
    """
    __tablename__ = "technology_radar_items"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False, default="WATCH")
    
    maturity: Mapped[str] = mapped_column(String(50), default="experimental")  # experimental, beta, production
    potential: Mapped[str] = mapped_column(String(50), default="high")  # low, medium, high
    cosa_use: Mapped[str] = mapped_column(String(50), default="pattern")  # pattern, direct, evaluated, none
    integration: Mapped[str] = mapped_column(String(20), default="no")  # yes, no, partial
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_reviewed: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
