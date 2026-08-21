from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, BigInteger, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db.base_class import Base
from core.snowflake import generate_snowflake_id

# Task/TaskDependency/TaskSchedule moved to core/tasks/models.py (COSA Structure.md
# §49 Business Core migration, Phase 1). Re-exported here for backward compatibility
# with existing `from founder_os.tasks.models import Task` call sites.
from business_core.tasks.models import Task, TaskDependency, TaskSchedule  # noqa: F401

class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint('workspace_id', 'slug', name='uix_agent_workspace_slug'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
