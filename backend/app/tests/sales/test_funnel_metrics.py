from unittest.mock import MagicMock
from app.business.sales.domain.funnel import FunnelMetricsService
from app.business.sales.models import SalesOpportunity


def test_funnel_metrics_calculation():
    db = MagicMock()
    # Mock lead counts
    db.query().filter().scalar.side_effect = [10, 4, 2, 5, 1]  # total_leads, qualified_leads, converted_leads, total_opps, won_opps

    # Mock open opps
    opp1 = SalesOpportunity(id=1, product="SaaS A", stage="DISCOVERY", estimated_value=10000.0, probability=None)
    opp2 = SalesOpportunity(id=2, product="SaaS B", stage="NEGOTIATION", estimated_value=50000.0, probability=0.9)
    db.query().filter().all.return_value = [opp1, opp2]

    metrics = FunnelMetricsService.get_funnel_metrics(db, workspace_id=1)

    assert metrics["total_leads"] == 10
    assert metrics["qualified_leads"] == 4
    assert metrics["lead_to_qualified_rate"] == 0.4
    assert metrics["pipeline_value"] == 60000.0
    # opp1 weighted: 10000 * 0.1 = 1000. opp2 weighted: 50000 * 0.9 = 45000. total weighted = 46000
    assert metrics["weighted_pipeline"] == 46000.0
