"""Unit tests for CEO Brief DSPy Program."""

import pytest
from app.ai.programs.ceo_brief.program import CEOBriefProgram
from app.ai.programs.schemas import CEOBriefInput, CEOBriefOutput


def test_ceo_brief_program_schema_validation():
    """Verify input/output schemas for CEO Brief program."""
    program = CEOBriefProgram()
    assert program.program_key == "ceo.brief"
    assert program.output_schema == CEOBriefOutput

    # Run forward pass (with predictor mock or default)
    result = program.forward(
        company_cycle={"name": "Q3 Scale", "target": "100k ARR"},
        okr_deltas=[{"kr": "MRR", "delta": "+10%"}],
        weekly_mission={"goal": "Close enterprise pilots"},
        sales_signals=[{"lead": "Acme Corp", "status": "Hot"}],
        finance_signals=[],
        legal_tech_signals=[],
        pending_approvals=[{"item": "Budget sign-off"}],
    )

    # Validate output structure
    validated = CEOBriefOutput.model_validate(result)
    assert validated.headline != ""
    assert isinstance(validated.wins, list)
    assert isinstance(validated.risks, list)
    assert isinstance(validated.today_top_3, list)
