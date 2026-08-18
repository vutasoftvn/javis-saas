from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.snowflake import generate_snowflake_id
from app.db.base_class import Base


class AccountingProfile(Base):
    __tablename__ = "accounting_profiles"
    __table_args__ = (UniqueConstraint("workspace_id", name="uq_accounting_profile_workspace"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    mode: Mapped[str] = mapped_column(String(30), default="TT58_MODE_1")
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    confirmed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AccountingRegulation(Base):
    __tablename__ = "accounting_regulations"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    jurisdiction: Mapped[str] = mapped_column(String(10), default="VN")
    title: Mapped[str] = mapped_column(String(255))


class AccountingRegulationVersion(Base):
    __tablename__ = "accounting_regulation_versions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    regulation_id: Mapped[int] = mapped_column(ForeignKey("accounting_regulations.id"), index=True)
    version: Mapped[str] = mapped_column(String(50))
    effective_date: Mapped[date] = mapped_column(Date)
    metadata_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


class AccountingBookTemplate(Base):
    __tablename__ = "accounting_book_templates"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    regulation_version_id: Mapped[int] = mapped_column(ForeignKey("accounting_regulation_versions.id"), index=True)
    mode: Mapped[str] = mapped_column(String(30))
    code: Mapped[str] = mapped_column(String(50))
    columns_schema: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")


class FinancialStatementTemplate(Base):
    __tablename__ = "financial_statement_templates"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    regulation_version_id: Mapped[int] = mapped_column(ForeignKey("accounting_regulation_versions.id"), index=True)
    mode: Mapped[str] = mapped_column(String(30))
    code: Mapped[str] = mapped_column(String(50))
    schema_jsonb: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")


class AccountingDocument(Base):
    __tablename__ = "accounting_documents"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    artifact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("artifacts.id"), nullable=True)
    document_no: Mapped[str] = mapped_column(String(100))
    document_date: Mapped[date] = mapped_column(Date)
    document_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounting_documents.id"), nullable=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True)
    cycle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("twelve_week_cycles.id"), nullable=True)
    work_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    transaction_date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    direction: Mapped[str] = mapped_column(String(10))
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AccountingRecord(Base):
    __tablename__ = "accounting_records"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("financial_transactions.id"), index=True)
    book_template_id: Mapped[int] = mapped_column(ForeignKey("accounting_book_templates.id"), index=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("accounting_periods.id"), index=True)
    row_data: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AccountingPeriod(Base):
    __tablename__ = "accounting_periods"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    closed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class FinanceException(Base):
    __tablename__ = "finance_exceptions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    transaction_id: Mapped[Optional[int]] = mapped_column(ForeignKey("financial_transactions.id"), nullable=True)
    exception_type: Mapped[str] = mapped_column(String(50), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="WARNING")
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FinanceManagementSnapshot(Base):
    __tablename__ = "finance_management_snapshots"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    cycle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("twelve_week_cycles.id"), nullable=True)
    as_of: Mapped[date] = mapped_column(Date)
    cash: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    burn: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    runway_months: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    revenue: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=0)
    expenses: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=0)
    budget_variance: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
