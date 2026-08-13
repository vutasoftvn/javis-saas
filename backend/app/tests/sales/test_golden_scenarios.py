from unittest.mock import MagicMock, patch
import pytest

from app.modules.sales.domain.opportunities import OpportunityService
from app.modules.sales.domain.leads import LeadService
from app.modules.company_runtime.blocker_router import BlockerRouter


def test_blocker_routing():
    assert BlockerRouter.route_blocker_function("Legal term review", "LEGAL_REVIEW") == "LEGAL"
    assert BlockerRouter.route_blocker_function("Tech query", "TECHNICAL_QUESTION") == "TECH"
    assert BlockerRouter.route_blocker_function("Pricing approval", "PRICING_NEEDED") == "FINANCE"


@patch("app.modules.sales.domain.leads.HandoffService.accept_handoff")
def test_golden_scenario_a_marketing_intake_dedupe(mock_accept):
    db = MagicMock()
    # Mock handoff
    handoff = MagicMock()
    handoff.id = 100
    handoff.workspace_id = 1
    handoff.artifact_refs = [
        {"name": "Alice", "email": "alice@acme.com", "company": "Acme Corp"},
        {"name": "Bob", "email": "bob@beta.com", "company": "Beta Ltd"},
    ]
    db.query().filter().first.side_effect = [handoff, None, None, None, None, None]

    with patch("app.modules.sales.domain.leads.ContactService.create_contact") as mock_contact, \
         patch("app.modules.sales.domain.leads.AccountService.create_account") as mock_acc, \
         patch("app.modules.sales.domain.leads.LeadService.create_lead") as mock_lead:
        
        mock_c = MagicMock(id=201)
        mock_a = MagicMock(id=301, name="Acme")
        mock_contact.return_value = mock_c
        mock_acc.return_value = mock_a
        mock_l = MagicMock(id=401)
        mock_lead.return_value = mock_l

        res = LeadService.intake_from_handoff(db, workspace_id=1, handoff_id=100)

        assert "created_leads" in res
        assert mock_accept.called
