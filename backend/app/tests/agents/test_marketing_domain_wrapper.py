import pytest
from unittest.mock import MagicMock, patch

from app.workforce.agents.domains.marketing import (
    MarketingDataCapability,
    MarketingReasoningCapability,
    MarketingResearchCapability,
    MarketingCommunicationCapability,
    MarketingActionCapability,
    MarketingEvaluationCapability,
)


def test_marketing_capabilities_standalone():
    mock_db = MagicMock()

    # 1. Data Capability
    with patch("app.business.marketing.services.funnel_engine.FunnelEngine.build_funnel", return_value={"stages": []}), \
         patch("app.business.marketing.services.scorecard_service.ScorecardService.build", return_value={"score": 85}):
        data_res = MarketingDataCapability.read_marketing_overview(db=mock_db, workspace_id=12345)
        assert data_res["status"] == "success"
        assert data_res["scorecard"]["score"] == 85

    # 2. Reasoning Capability
    reasoning_res = MarketingReasoningCapability.analyze_funnel_bottlenecks()
    assert reasoning_res["status"] == "success"
    assert "bottlenecks" in reasoning_res

    # 3. Research Capability
    research_res = MarketingResearchCapability.research_campaign_angles(target_audience="Founders")
    assert research_res["status"] == "success"
    assert len(research_res["angles"]) >= 2

    # 4. Communication Capability
    comm_res = MarketingCommunicationCapability.generate_campaign_drafts(topic="Agentic Automation")
    assert comm_res["status"] == "success"
    assert len(comm_res["drafts"]) >= 2

    # 5. Action Capability
    action_res = MarketingActionCapability.prepare_campaign_launch(
        db=mock_db,
        workspace_id=12345,
        campaign_name="Q1 Inbound Growth",
    )
    assert action_res["status"] == "success"
    assert action_res["launch_package"]["approval_level"] == "L3A_EXECUTE_WITH_APPROVAL"

    # 6. Evaluation Capability
    eval_res = MarketingEvaluationCapability.evaluate_campaign_health(cac=45.0, target_cac=60.0)
    assert eval_res["status"] == "success"
    assert eval_res["health"] == "HEALTHY"
