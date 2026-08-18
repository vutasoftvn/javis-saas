"""Pytest suite for Phase P0: Centralized Prompt Registry."""

import pytest
from pathlib import Path
from app.workforce.ai.prompt_registry import PromptRegistry


def test_prompt_registry_load_and_render():
    """Prompt templates must be loaded, versioned, and rendered with variables."""
    registry = PromptRegistry()
    templates = registry.list_templates()
    
    # Check that core domain templates exist
    assert "cosa/system" in templates
    assert "cosa/founder_brief" in templates
    assert "sales/prospect" in templates
    assert "marketing/campaign" in templates
    assert "finance/finance_brief" in templates
    assert "legal/contract_review" in templates

    # Check rendering
    rendered = registry.render(
        "cosa", "system",
        {"founder_name": "Tony", "workspace_name": "Acme Corp"}
    )
    assert "Tony" in rendered
    assert "Acme Corp" in rendered

    # Check version format
    template = registry.get("cosa", "system")
    assert template is not None
    assert template.version.startswith("cosa.system.")
    assert len(template.sha256) == 64
