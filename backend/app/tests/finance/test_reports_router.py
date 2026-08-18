from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.business.finance.routers.reports_router import list_reports


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_):
        return self

    def order_by(self, *_):
        return self

    def limit(self, *_):
        return self

    def all(self):
        return self.rows


class _Db:
    def __init__(self, rows):
        self.rows = rows

    def query(self, _):
        return _Query(self.rows)


def test_reports_returns_management_snapshots_for_the_workspace():
    snapshot = SimpleNamespace(
        id=12,
        cycle_id=34,
        as_of=date(2026, 8, 1),
        cash=Decimal("1200000.00"),
        burn=Decimal("300000.00"),
        runway_months=Decimal("4.00"),
        revenue=Decimal("700000.00"),
        expenses=Decimal("250000.00"),
        budget_variance=Decimal("-10000.00"),
    )

    response = list_reports(workspace_id=1, member=SimpleNamespace(), db=_Db([snapshot]))

    assert response == {"reports": [{
        "id": "12", "cycle_id": "34", "as_of": "2026-08-01",
        "cash": "1200000.00", "burn": "300000.00", "runway_months": "4.00",
        "revenue": "700000.00", "expenses": "250000.00", "budget_variance": "-10000.00",
    }]}
