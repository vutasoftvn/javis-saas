"""create V13 deterministic Finance core tables

Revision ID: v13_005_finance
Revises: v13_004_functions
"""
from typing import Sequence, Union

from alembic import op

from app.modules.finance.models import (
    AccountingProfile, AccountingRegulation, AccountingRegulationVersion,
    AccountingBookTemplate, FinancialStatementTemplate, AccountingDocument,
    FinancialTransaction, AccountingPeriod, AccountingRecord, FinanceException,
    FinanceManagementSnapshot,
)

revision: str = "v13_005_finance"
down_revision: Union[str, Sequence[str], None] = "v13_004_functions"
branch_labels = None
depends_on = None

TABLES = (
    AccountingProfile.__table__, AccountingRegulation.__table__,
    AccountingRegulationVersion.__table__, AccountingBookTemplate.__table__,
    FinancialStatementTemplate.__table__, AccountingDocument.__table__,
    FinancialTransaction.__table__, AccountingPeriod.__table__,
    AccountingRecord.__table__, FinanceException.__table__,
    FinanceManagementSnapshot.__table__,
)


def upgrade() -> None:
    bind = op.get_bind()
    for table in TABLES:
        table.create(bind=bind, checkfirst=False)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(TABLES):
        table.drop(bind=bind, checkfirst=False)
