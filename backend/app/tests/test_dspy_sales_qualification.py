"""Unit tests for Sales Lead Qualification DSPy Program."""

import pytest
from app.ai.programs.sales.lead_qualification import LeadQualificationProgram
from app.ai.programs.schemas import LeadQualificationOutput


def test_sales_lead_qualification_output_schema():
    """Verify LeadQualificationProgram structure and output bounds."""
    program = LeadQualificationProgram()
    assert program.program_key == "sales.lead_qualification"
    assert program.output_schema == LeadQualificationOutput

    result = program.forward(
        lead={"name": "Alice Smith", "company": "TechGlobal Inc", "employees": 250},
        company_context={"product": "COSA OS", "price": "$500/mo"},
        interaction_history=[
            {"role": "lead", "text": "We need an AI operating system for our 50-person ops team ASAP."}
        ],
        icp_profile={"target_size": "50-500", "industry": "Technology"},
    )

    validated = LeadQualificationOutput.model_validate(result)
    assert 0.0 <= validated.fit_score <= 1.0
    assert 0.0 <= validated.need_score <= 1.0
    assert 0.0 <= validated.timing_score <= 1.0
    assert 0.0 <= validated.confidence <= 1.0
    assert validated.recommended_stage in ["discovery", "qualified", "nurture", "disqualified"]
    assert len(validated.recommended_next_action) > 0
