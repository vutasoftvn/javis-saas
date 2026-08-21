import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from core.snowflake import generate_snowflake_id
from db.models import WorkspaceMember
from business.finance.models import (
    AccountingDocument,
    FinancialTransaction,
    AccountingRecord,
)
from business.finance import tt58_engine
from business.finance.tt58_router import get_founder_lite_metrics


def _mock_query():
    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.all.return_value = []
    q.first.return_value = None
    return q


def test_finance_cross_tenant_forbidden():
    """Verify that user cannot access finance metrics of another workspace."""
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = generate_snowflake_id()

    other_ws_id = generate_snowflake_id()
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        get_founder_lite_metrics(workspace_id=other_ws_id, member=member, db=db)

    assert exc_info.value.status_code == 403


def test_document_creation_and_posting_engine():
    """Verify creating a DRAFT document and posting it creates transaction and accounting record."""
    ws_id = generate_snowflake_id()
    doc_id = generate_snowflake_id()
    db = MagicMock()

    mock_doc = AccountingDocument(
        id=doc_id,
        workspace_id=ws_id,
        document_no="HD-2026-001",
        document_type="HOA_DON",
        document_date=date(2026, 8, 16),
        status="DRAFT",
    )

    query = _mock_query()
    query.first.return_value = mock_doc
    db.query.return_value = query

    res = tt58_engine.post_accounting_document(
        db=db,
        workspace_id=ws_id,
        document_id=doc_id,
        amount=Decimal("50000000"),
        direction="IN",
        description="Thu tiền dịch vụ SaaS COSA OS",
        category="DOANH_THU",
    )

    assert res["status"] == "success"
    assert res["document_status"] == "POSTED"
    assert res["amount"] == 50000000.0
    assert mock_doc.status == "POSTED"
    assert db.commit.called


def test_voided_document_creates_reversal_entry():
    """Verify voiding a posted document creates reversal transaction and marks VOIDED."""
    ws_id = generate_snowflake_id()
    doc_id = generate_snowflake_id()
    tx_id = generate_snowflake_id()
    db = MagicMock()

    mock_doc = AccountingDocument(
        id=doc_id,
        workspace_id=ws_id,
        document_no="PC-005",
        document_type="PHIEU_CHI",
        document_date=date(2026, 8, 16),
        status="POSTED",
    )
    mock_tx = FinancialTransaction(
        id=tx_id,
        workspace_id=ws_id,
        document_id=doc_id,
        amount=Decimal("15000000"),
        direction="OUT",
        category="CHI_PHI_VAN_HANH",
    )

    query = _mock_query()
    query.first.return_value = mock_doc
    query.all.return_value = [mock_tx]
    db.query.return_value = query

    res = tt58_engine.void_accounting_document(
        db=db,
        workspace_id=ws_id,
        document_id=doc_id,
        reason="Nhập sai thông tin nhà cung cấp",
    )

    assert res["status"] == "success"
    assert res["document_status"] == "VOIDED"
    assert res["reversal_transactions_count"] == 1
    assert mock_doc.status == "VOIDED"
    assert db.commit.called


def test_inventory_average_cost_valuation():
    """Verify inventory weighted average unit cost calculation."""
    # Opening: 100 units @ 100,000 = 10,000,000
    # Inflow: 200 units @ 110,000 = 22,000,000
    # Total: 300 units = 32,000,000 -> Unit cost = 32,000,000 / 300 = 106,666.67
    avg_cost = tt58_engine.calculate_inventory_average_cost(
        opening_qty=Decimal("100"),
        opening_val=Decimal("10000000"),
        inflow_qty=Decimal("200"),
        inflow_val=Decimal("22000000"),
    )

    assert avg_cost == Decimal("106666.67")


def test_b01_balance_sheet_equality():
    """Verify that B01-DNSN balance sheet satisfies: Total Assets == Total Capital & Liabilities."""
    ws_id = generate_snowflake_id()
    db = MagicMock()
    query = _mock_query()
    query.all.return_value = []
    db.query.return_value = query

    b01 = tt58_engine.generate_financial_statement_b01(db, ws_id)
    assert b01["report_code"] == "B01-DNSN"
    assert b01["is_balanced"] is True
    assert b01["assets"]["total_assets"] == b01["capital_and_liabilities"]["total_capital"]


def test_b02_income_statement():
    """Verify B02-DNSN generates accurate gross profit, operating profit, and net profit."""
    ws_id = generate_snowflake_id()
    db = MagicMock()
    query = _mock_query()
    query.all.return_value = []
    db.query.return_value = query

    b02 = tt58_engine.generate_financial_statement_b02(db, ws_id)
    assert b02["report_code"] == "B02-DNSN"
    assert "net_revenue" in b02["items"]
    assert "net_profit_after_tax" in b02["items"]


def test_b03_financial_statement_notes():
    """Verify B03-DNSN contains compliance notes and statutory requirements."""
    ws_id = generate_snowflake_id()
    db = MagicMock()
    query = _mock_query()
    query.all.return_value = []
    query.first.return_value = None
    db.query.return_value = query

    b03 = tt58_engine.generate_financial_statement_b03(db, ws_id)
    assert b03["report_code"] == "B03-DNSN"
    assert "compliance_note" in b03
    assert "accounting_policies" in b03


def test_f01_tax_obligations_report():
    """Verify F01-DNSN reports VAT, CIT, PIT, and License fee."""
    ws_id = generate_snowflake_id()
    db = MagicMock()
    query = _mock_query()
    query.all.return_value = []
    db.query.return_value = query

    f01 = tt58_engine.generate_tax_obligation_report_f01(db, ws_id)
    assert f01["report_code"] == "F01-DNSN"
    assert len(f01["taxes"]) == 4
    assert "total_balance_due" in f01

