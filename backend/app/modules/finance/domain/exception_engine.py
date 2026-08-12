from datetime import date


EXCEPTION_TYPES = {
    "MISSING_DOCUMENT", "DUPLICATE_DOCUMENT", "FUTURE_DATE", "ZERO_AMOUNT",
    "MISSING_CATEGORY", "NEGATIVE_AMOUNT", "PERIOD_LOCKED", "MODE_CONFLICT",
    "UNBALANCED_RECORD", "MISSING_COUNTERPARTY", "LARGE_CASH_MOVEMENT", "INVALID_REFERENCE",
}


def detect_exceptions(transaction: dict, *, today: date, locked: bool = False) -> list[dict]:
    found = []
    if not transaction.get("document_id"):
        found.append({"type": "MISSING_DOCUMENT", "severity": "WARNING"})
    if transaction.get("transaction_date") and transaction["transaction_date"] > today:
        found.append({"type": "FUTURE_DATE", "severity": "ERROR"})
    if transaction.get("amount") == 0:
        found.append({"type": "ZERO_AMOUNT", "severity": "ERROR"})
    if transaction.get("amount", 0) < 0:
        found.append({"type": "NEGATIVE_AMOUNT", "severity": "ERROR"})
    if not transaction.get("category"):
        found.append({"type": "MISSING_CATEGORY", "severity": "WARNING"})
    if locked:
        found.append({"type": "PERIOD_LOCKED", "severity": "ERROR"})
    return found
