from app.business.sales.domain.opportunities import OpportunityStageService


def test_legal_stage_transitions():
    assert OpportunityStageService.can_transition("DISCOVERY", "QUALIFIED") is True
    assert OpportunityStageService.can_transition("DISCOVERY", "LOST") is True
    assert OpportunityStageService.can_transition("QUALIFIED", "SOLUTION") is True
    assert OpportunityStageService.can_transition("SOLUTION", "PROPOSAL") is True
    assert OpportunityStageService.can_transition("PROPOSAL", "NEGOTIATION") is True
    assert OpportunityStageService.can_transition("NEGOTIATION", "WON") is True


def test_illegal_stage_transitions():
    assert OpportunityStageService.can_transition("DISCOVERY", "WON") is False
    assert OpportunityStageService.can_transition("DISCOVERY", "PROPOSAL") is False
    assert OpportunityStageService.can_transition("WON", "DISCOVERY") is False
    assert OpportunityStageService.can_transition("LOST", "WON") is False
