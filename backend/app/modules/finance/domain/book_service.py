from decimal import Decimal


def _plain(value: Decimal) -> str:
    return format(value, "f")


def build_s1_dnsn_rows(transactions: list[dict]) -> list[dict]:
    balance = Decimal("0")
    rows = []
    for line_no, transaction in enumerate(transactions, start=1):
        cash_in = Decimal(transaction.get("cash_in", 0))
        cash_out = Decimal(transaction.get("cash_out", 0))
        balance += cash_in - cash_out
        rows.append({
            "line_no": line_no,
            "date": transaction["date"],
            "document_no": transaction["document_no"],
            "description": transaction["description"],
            "cash_in": _plain(cash_in),
            "cash_out": _plain(cash_out),
            "balance": _plain(balance),
        })
    return rows
