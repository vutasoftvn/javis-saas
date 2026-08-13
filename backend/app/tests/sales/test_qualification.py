from app.modules.sales.domain.qualification import QualificationService


def test_qualification_all_present_qualified():
    status, reason = QualificationService.qualify(
        fit="HIGH",
        need="EXPANSION",
        urgency="Q3",
        authority="DECISION_MAKER",
        ability_to_pay="YES",
    )
    assert status == "QUALIFIED"
    assert reason is None


def test_qualification_hard_fail_ability_to_pay():
    status, reason = QualificationService.qualify(
        fit="HIGH",
        need="EXPANSION",
        urgency="Q3",
        authority="DECISION_MAKER",
        ability_to_pay="NO",
    )
    assert status == "DISQUALIFIED"
    assert "Ability to pay" in reason


def test_qualification_missing_dimension():
    status, reason = QualificationService.qualify(
        fit="HIGH",
        need="EXPANSION",
        urgency=None,
        authority="DECISION_MAKER",
        ability_to_pay="YES",
    )
    assert status == "NEEDS_DISCOVERY"
    assert "urgency" in reason
