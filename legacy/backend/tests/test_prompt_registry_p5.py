"""Test suite for Prompt Registry & Candidate Lifecycle in P5 (Spec §30, §56–§60)."""

import pytest
from workforce.ai.prompt_registry import PromptRegistry, PromptTemplate, PromptCandidate


def test_prompt_registry_loads_all_domains():
    """Test that PromptRegistry loads standard templates across 6 domains."""
    registry = PromptRegistry.get_instance()
    registry.reload()
    templates = registry.list_templates()
    
    # Verify core domain templates exist
    assert "cosa/system" in templates or "cosa/conversation_guard" in templates
    assert "sales/outbound" in templates
    assert "sales/qualify" in templates
    assert "sales/proposal" in templates
    assert "marketing/research" in templates
    assert "marketing/campaign" in templates
    assert "marketing/landing_page" in templates
    assert "finance/analyze" in templates
    assert "legal/review" in templates
    assert "quality/judge" in templates


def test_prompt_render_variable_substitution():
    """Test variable rendering and missing template handling."""
    registry = PromptRegistry.get_instance()
    rendered = registry.render(
        domain="sales",
        name="outbound",
        variables={
            "company_name": "Acme Corp",
            "icp_criteria": "B2B SaaS with > 50 employees",
        },
    )
    assert "Acme Corp" in rendered
    assert "B2B SaaS with > 50 employees" in rendered

    with pytest.raises(KeyError):
        registry.render("unknown_domain", "missing_prompt")


def test_prompt_candidate_lifecycle_and_promotion():
    """Test candidate registration, evaluation recording, and governed promotion."""
    registry = PromptRegistry.get_instance()
    
    # 1. Register candidate
    cand = registry.register_candidate(
        domain="finance",
        name="cashflow_forecast",
        content="Forecast cashflow for ${months} months.",
        base_version="1.0.0",
        proposed_by_agent="finance_specialist",
    )
    assert cand.status == "candidate"
    assert cand.domain == "finance"
    assert "months" in cand.variables

    # 2. Record eval
    evaluated_cand = registry.record_candidate_eval(
        candidate_id=cand.candidate_id,
        eval_score=0.92,
        eval_metrics={"accuracy": 0.95, "brevity": 0.89},
        notes="Outperformed baseline in 5 test cases",
    )
    assert evaluated_cand.status == "evaluated"
    assert evaluated_cand.eval_score == 0.92

    # 3. Promote candidate by Admin
    promoted = registry.promote_candidate(
        candidate_id=cand.candidate_id,
        approved_by_user_id=42,
    )
    assert promoted.approved_by == 42
    assert promoted.is_active is True

    # 4. Verify rendered from active template map
    retrieved = registry.get("finance", "cashflow_forecast")
    assert retrieved is not None
    assert retrieved.content == "Forecast cashflow for ${months} months."


def test_prompt_candidate_rejection():
    """Test rejecting a candidate prompt."""
    registry = PromptRegistry.get_instance()
    cand = registry.register_candidate(
        domain="legal",
        name="auto_nda",
        content="Generate NDA without legal disclaimer.",
        base_version="1.0.0",
    )
    rejected = registry.reject_candidate(
        candidate_id=cand.candidate_id,
        rejected_by_user_id=1,
        reason="Missing mandatory legal disclaimer",
    )
    assert rejected.status == "rejected"
    assert rejected.rejection_reason == "Missing mandatory legal disclaimer"
