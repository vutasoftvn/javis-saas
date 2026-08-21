from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base_class import Base
from core.snowflake import generate_snowflake_id


class Organization(Base):
    """Mô hình Organization - Doanh nghiệp / Tổ chức gắn với Workspace (§139–171)."""
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Department(Base):
    """Mô hình Department - Phòng ban chức năng trong tổ chức (§167)."""
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    is_ai_only: Mapped[bool] = mapped_column(Boolean, default=False)
    capability_domain: Mapped[str] = mapped_column(String(50))  # ceo_office, product_tech, marketing, operations, finance, legal
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkforceMember(Base):
    """Mô hình WorkforceMember - Nhân sự hỗn hợp (Người thật hoặc Tác tử AI) (§140)."""
    __tablename__ = "workforce_members"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    member_type: Mapped[str] = mapped_column(String(20))  # HUMAN, AI_AGENT
    human_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    agent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    # Quyết định 4.3c - dần thay agent_id (FK bảng agents cũ) bằng
    # agent_definition_id (FK agent_definitions, canonical AI employee record).
    agent_definition_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("agent_runtime.agent_definitions.id"), nullable=True, index=True
    )
    role_title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, paused, archived
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DepartmentMembership(Base):
    """Mô hình DepartmentMembership - Thành viên trực thuộc phòng ban."""
    __tablename__ = "department_memberships"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    member_id: Mapped[int] = mapped_column(ForeignKey("workforce_members.id"), index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    role: Mapped[str] = mapped_column(String(50), default="member")  # head, member, reviewer
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentRelation(Base):
    """Mô hình AgentRelation - Quan hệ phân cấp & trách nhiệm của tác tử AI (§145)."""
    __tablename__ = "agent_relations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    related_member_id: Mapped[int] = mapped_column(ForeignKey("workforce_members.id"), index=True)
    relation: Mapped[str] = mapped_column(String(50), default="operator")  # owner, manager, operator, reviewer, approver
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkforceRelation(Base):
    """WorkforceRelation - org-chart THẬT của công ty (Quyết định 4.3d): quan hệ
    phân cấp/trách nhiệm giữa các WorkforceMember bất kể Human hay AI (vd Founder
    quản CFO Agent, Human CTO quản AI Software Engineer). Thay cho AgentRelation
    (agent_id chỉ trỏ Agent AI, không mô tả được quan hệ Human<->AI). AgentRelation
    được GIỮ NGUYÊN (không xoá) - xem docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md.
    """
    __tablename__ = "workforce_relations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("workforce_members.id"), index=True)
    related_member_id: Mapped[int] = mapped_column(ForeignKey("workforce_members.id"), index=True)
    relation: Mapped[str] = mapped_column(String(50), default="reports_to")  # owner, manager, operator, reviewer, approver, reports_to
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("member_id", "related_member_id", "relation", name="uq_workforce_relation_edge"),
    )
