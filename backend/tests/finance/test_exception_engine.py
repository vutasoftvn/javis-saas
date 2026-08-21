from datetime import date, timedelta

from business.finance.domain.exception_engine import EXCEPTION_TYPES, detect_exceptions


def test_exception_catalog_contains_all_twelve_rule_types():
    assert len(EXCEPTION_TYPES) == 12


def test_detects_missing_evidence_and_future_zero_transaction():
    exceptions = detect_exceptions(
        {"document_id": None, "transaction_date": date.today() + timedelta(days=1), "amount": 0, "category": None},
        today=date.today(),
    )
    assert {item["type"] for item in exceptions} == {"MISSING_DOCUMENT", "FUTURE_DATE", "ZERO_AMOUNT", "MISSING_CATEGORY"}
