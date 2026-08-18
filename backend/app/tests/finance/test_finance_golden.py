from decimal import Decimal

from app.business.finance.domain.book_service import build_s1_dnsn_rows


def test_documents_to_s1_dnsn_rows_golden_fixture():
    transactions = [
        {"date": "2026-01-02", "document_no": "PT001", "description": "Founder capital", "cash_in": Decimal("50000000"), "cash_out": Decimal("0")},
        {"date": "2026-01-03", "document_no": "PC001", "description": "Hosting", "cash_in": Decimal("0"), "cash_out": Decimal("1200000")},
    ]
    assert build_s1_dnsn_rows(transactions) == [
        {"line_no": 1, "date": "2026-01-02", "document_no": "PT001", "description": "Founder capital", "cash_in": "50000000", "cash_out": "0", "balance": "50000000"},
        {"line_no": 2, "date": "2026-01-03", "document_no": "PC001", "description": "Hosting", "cash_in": "0", "cash_out": "1200000", "balance": "48800000"},
    ]
