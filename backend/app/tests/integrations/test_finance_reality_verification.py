"""Integration Tests for Financial Reality Verifier & TT58 Certification (§P0.7, §P4, C1/C2 Spec).

Verifies that RealityVerifier performs database reality checks on AccountingDocument,
FinancialTransaction, and ledger AccountingRecords before issuing Outcome Certificates.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock
import pytest
from sqlalchemy.orm import Session

from app.workforce.agents.verification.reality_verifier import (
    RealityVerifier,
    VerificationVerdict,
)
from app.core.snowflake import generate_snowflake_id
from app.business.finance.models import (
    AccountingDocument,
    AccountingRecord,
    FinancialTransaction,
)
from app.founder_os.outcomes.models import Outcome, OutcomeRun


def test_verify_accounting_document_success():
    mock_db = MagicMock()
    doc_id = generate_snowflake_id()
    mock_doc = AccountingDocument(
        id=doc_id,
        workspace_id=1,
        document_no="PT001",
        document_type="PHIEU_THU",
        document_date=date(2026, 8, 16),
        status="POSTED",
    )

    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_doc
    mock_db.execute.return_value = mock_execute

    result = RealityVerifier.verify_accounting_document(
        db=mock_db,
        workspace_id=1,
        document_id=doc_id,
        expected_status="POSTED",
        expected_document_no="PT001",
        expected_document_type="PHIEU_THU",
    )

    assert result.verdict == VerificationVerdict.VERIFIED
    assert len(result.evidence) == 1
    assert result.evidence[0].domain == "finance"
    assert result.evidence[0].resource_type == "accounting_document"
    assert result.evidence[0].details.get("status") == "POSTED"


def test_verify_accounting_document_status_mismatch():
    mock_db = MagicMock()
    doc_id = generate_snowflake_id()
    mock_doc = AccountingDocument(
        id=doc_id,
        workspace_id=1,
        document_no="PT001",
        document_type="PHIEU_THU",
        document_date=date(2026, 8, 16),
        status="DRAFT",
    )

    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_doc
    mock_db.execute.return_value = mock_execute

    result = RealityVerifier.verify_accounting_document(
        db=mock_db,
        workspace_id=1,
        document_id=doc_id,
        expected_status="POSTED",
    )

    assert result.verdict == VerificationVerdict.FAILED
    assert any("mismatch" in err.lower() for err in result.unresolved)


def test_verify_financial_transaction_with_ledger_records():
    mock_db = MagicMock()
    tx_id = generate_snowflake_id()
    mock_tx = FinancialTransaction(
        id=tx_id,
        workspace_id=1,
        document_id=1001,
        transaction_date=date(2026, 8, 16),
        description="Thu tien ban hang",
        amount=Decimal("50000000"),
        direction="IN",
        category="DOANH_THU",
    )

    mock_record = AccountingRecord(
        id=generate_snowflake_id(),
        workspace_id=1,
        transaction_id=tx_id,
        book_template_id=2001,
        period_id=3001,
        row_data={"amount": 50000000, "direction": "IN"},
    )

    def mock_execute_side_effect(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "financial_transactions" in stmt_str:
            mock_result.scalar_one_or_none.return_value = mock_tx
        elif "accounting_records" in stmt_str:
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = [mock_record]
            mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_db.execute.side_effect = mock_execute_side_effect

    result = RealityVerifier.verify_financial_transaction(
        db=mock_db,
        workspace_id=1,
        transaction_id=tx_id,
        expected_direction="IN",
        expected_category="DOANH_THU",
    )

    assert result.verdict == VerificationVerdict.VERIFIED
    assert len(result.evidence) == 1
    assert result.evidence[0].domain == "finance"
    assert result.evidence[0].resource_type == "financial_transaction"
    assert result.evidence[0].details.get("has_accounting_record") is True
    assert result.evidence[0].details.get("records_count") == 1


def test_financial_outcome_certificate_minting():
    mock_db = MagicMock()
    outcome_id = generate_snowflake_id()
    run_id = generate_snowflake_id()

    mock_run = OutcomeRun(
        id=run_id,
        outcome_id=outcome_id,
        status="running",
    )
    mock_exec = MagicMock()
    mock_exec.scalar_one_or_none.return_value = mock_run
    mock_db.execute.return_value = mock_exec
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()

    doc_id = generate_snowflake_id()
    mock_doc = AccountingDocument(
        id=doc_id,
        workspace_id=1,
        document_no="PT999",
        document_type="PHIEU_THU",
        document_date=date(2026, 8, 16),
        status="POSTED",
    )
    mock_exec_doc = MagicMock()
    mock_exec_doc.scalar_one_or_none.return_value = mock_doc
    mock_db.execute.side_effect = [mock_exec_doc, mock_exec]

    verif_res = RealityVerifier.verify_accounting_document(
        db=mock_db,
        workspace_id=1,
        document_id=doc_id,
        expected_status="POSTED",
    )

    cert_artifact = RealityVerifier.create_outcome_certificate(
        db=mock_db,
        workspace_id=1,
        outcome_id=outcome_id,
        run_id=run_id,
        verification_result=verif_res,
        user_id=1,
    )

    assert cert_artifact is not None
    assert cert_artifact.type == "external_action_receipt"
    assert cert_artifact.status == "approved"
    assert "VERIFIED" in cert_artifact.title
    assert mock_run.verification_status == "VERIFIED"
