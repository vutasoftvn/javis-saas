from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, UniqueConstraint, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint('workspace_id', 'idempotency_key', name='uix_task_workspace_idempotency_key'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    title: Mapped[str] = mapped_column(String(1024))
    # Header "Idempotency-Key" của client, để gửi trùng request tạo Task không tạo bản
    # ghi thứ 2 (Postgres coi nhiều NULL là phân biệt nên không ảnh hưởng task không
    # gửi kèm key). Xem §13 "mọi mutating request hỗ trợ header Idempotency-Key".
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="todo") # todo, in_progress, waiting_approval, blocked, done, cancelled
    priority: Mapped[str] = mapped_column(String(50), default="medium") # low, medium, high, urgent
    planned_start_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    assignee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    completion_policy: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    initiative_id: Mapped[Optional[int]] = mapped_column(ForeignKey("initiatives.id"), nullable=True)
    weekly_commitment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("weekly_commitments.id"), nullable=True)
    sort_key: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Hybrid Workforce fields (mCOSA roadmap Phase 7, §150) - extends this
    # table rather than a parallel `work_items` table per the blueprint's
    # explicit "don't split the task engine" rule. Nullable/additive: no
    # existing tasks/router.py or TasksController behavior depends on these.
    assignee_member_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workforce_members.id"), nullable=True)
    owner_member_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workforce_members.id"), nullable=True)
    execution_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # HUMAN, AGENT, HYBRID
    function: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    depends_on_task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    dependency_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # BLOCKS, REQUIRES_OUTPUT, REQUIRES_APPROVAL, REQUIRES_DECISION, REQUIRES_DOCUMENT
    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PENDING, SATISFIED, FAILED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TaskSchedule(Base):
    __tablename__ = "task_schedules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    schedule_type: Mapped[str] = mapped_column(String(50)) # once, recurring
    cron_expr: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
