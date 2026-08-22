"""Database models for Report Automation Flows and Delivery History."""

from datetime import datetime, timezone
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship

from db.snowflake_model import SnowflakeIDMixin
from db.base import Base


class ReportAutomationFlow(Base, SnowflakeIDMixin):
    __tablename__ = "report_automation_flows"

    workspace_id = sa.Column(sa.BigInteger, sa.ForeignKey("core.workspaces.id"), nullable=False, index=True)
    user_id = sa.Column(sa.BigInteger, sa.ForeignKey("core.users.id"), nullable=False, index=True)
    name = sa.Column(sa.String(255), nullable=False)
    trigger_type = sa.Column(sa.String(50), nullable=False, server_default="cron")
    schedule_cron = sa.Column(sa.String(100), nullable=True)  # e.g., '0 9 * * 1'
    timezone = sa.Column(sa.String(50), nullable=False, server_default="Asia/Ho_Chi_Minh")
    scope = sa.Column(sa.String(50), nullable=False, server_default="cycle")
    channels = sa.Column(postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    status = sa.Column(sa.String(50), nullable=False, server_default="active")
    last_run_at = sa.Column(sa.DateTime(timezone=True), nullable=True)
    next_run_at = sa.Column(sa.DateTime(timezone=True), nullable=True)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    deliveries = relationship("ReportDeliveryHistory", back_populates="flow", cascade="all, delete-orphan")


class ReportDeliveryHistory(Base, SnowflakeIDMixin):
    __tablename__ = "report_delivery_history"

    flow_id = sa.Column(sa.BigInteger, sa.ForeignKey("report_automation_flows.id"), nullable=False, index=True)
    workspace_id = sa.Column(sa.BigInteger, sa.ForeignKey("core.workspaces.id"), nullable=False, index=True)
    status = sa.Column(sa.String(50), nullable=False, server_default="delivered")
    delivered_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    summary_text = sa.Column(sa.Text, nullable=True)
    payload_snapshot_jsonb = sa.Column(postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    error_message = sa.Column(sa.Text, nullable=True)

    flow = relationship("ReportAutomationFlow", back_populates="deliveries")
