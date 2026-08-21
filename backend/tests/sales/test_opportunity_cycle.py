from unittest.mock import MagicMock

from business.sales.domain.opportunities import OpportunityService
from business.sales.models import SalesOpportunity


def test_won_opportunity_passes_its_cycle_to_finance_handoff(monkeypatch):
    opportunity = SalesOpportunity(
        id=88,
        workspace_id=1,
        account_id=2,
        stage="NEGOTIATION",
        cycle_id=55,
        currency="VND",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [opportunity, None]
    handoff = MagicMock()
    monkeypatch.setattr("business.sales.domain.opportunities.HandoffService.create_handoff", handoff)
    monkeypatch.setattr("business.sales.domain.opportunities.ActivityService.record_status_change", MagicMock())

    OpportunityService.win_opportunity(db, 1, 88, "VALUE", actor_id=9)

    assert handoff.call_args.kwargs["cycle_id"] == 55
