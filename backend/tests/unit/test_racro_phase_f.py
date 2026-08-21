import pytest
from business.marketing.services.racro_orchestrate_service import (
    RACROOrchestrateService,
    MarketingPulseCard,
    FounderDailyBrief,
)
from business.marketing.schemas.racro_contracts import AttributionChainEvent


def test_record_attribution_event():
    service = RACROOrchestrateService()
    utm = {"utm_source": "facebook_ads", "utm_campaign": "spring_launch_2026"}

    event = service.record_attribution_event(
        workspace_id=1,
        campaign_id=101,
        lead_id=501,
        opportunity_id=901,
        revenue_amount=25000000.0,
        event_type="sale_closed",
        utm_params=utm,
    )

    assert isinstance(event, AttributionChainEvent)
    assert event.campaign_id == 101
    assert event.lead_id == 501
    assert event.revenue_amount == 25000000.0
    assert event.utm_source == "facebook_ads"
    assert event.utm_campaign == "spring_launch_2026"


def test_compute_marketing_pulse_card():
    service = RACROOrchestrateService()

    card = service.compute_marketing_pulse_card(
        workspace_id=1,
        project_stage="Validation",
        demand_signals_count=5,
        total_leads=40,
        qualified_leads=12,
        response_time_min=3.5,
        unresponded_leads=3,
    )

    assert isinstance(card, MarketingPulseCard)
    assert card.workspace_id == 1
    assert card.project_stage == "Validation"
    assert card.demand_signals_count == 5
    assert card.total_leads == 40
    assert card.qualified_leads == 12
    assert card.median_response_time_minutes == 3.5
    assert len(card.attention_alerts) == 1
    assert "3 leads chưa được liên hệ lại" in card.attention_alerts[0]
    assert "Offer B" in card.cosa_recommendation


def test_generate_founder_daily_brief():
    service = RACROOrchestrateService()

    brief = service.generate_founder_daily_brief(
        workspace_id=1,
        project_stage="Validation",
    )

    assert isinstance(brief, FounderDailyBrief)
    assert brief.workspace_id == 1
    assert len(brief.highlights) >= 2
    assert len(brief.action_items) >= 1
    assert brief.pulse.attributed_revenue_vnd > 0.0
