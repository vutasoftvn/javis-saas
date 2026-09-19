"""Tests for Startup Personas Integration (Solo Founder, Startup CTO, Growth Marketer).

Verifies:
1. `COSA_COFOUNDER_ASSISTANT_AGENT_SPEC` is registered, has L0_OBSERVE, contains the Solo Founder prompt heuristics.
2. `AGENT_PROFILE_SPECS['founder_assistant']` maps to `COSA_COFOUNDER_ASSISTANT_AGENT_SPEC`.
3. `AGENT_PROFILE_SPECS['cto']` maps to `COSA_EXECUTIVE_CTO_AGENT_SPEC`, which pins `executive.cto-advisor`.
4. `COSA_MARKETING_AGENT_SPEC` pins `growth.bootstrapped-engine` and `research.deep-research@1.2.0`.
5. Suggested personas in `FUNCTIONAL_AGENT_CATALOG` include "Growth Marketer" and "Solo Founder".
6. Pinned skills in `founder_assistant`, `marketing`, and `cto` resolve cleanly in `InMemorySpecRegistryRepository`.
"""

import pytest

from agent.governance.contracts import AutonomyLevel
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.skills.resolver import SkillResolver
from agent.workforce.catalog import FUNCTIONAL_AGENT_CATALOG
from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.seed import seed_builtin_skillpacks
from apps.cosa.agents.specs import (
    COSA_COFOUNDER_ASSISTANT_AGENT_SPEC,
    COSA_COFOUNDER_ASSISTANT_PROMPT,
    COSA_EXECUTIVE_CTO_AGENT_SPEC,
    COSA_EXECUTIVE_CTO_PROMPT,
    COSA_MARKETING_AGENT_SPEC,
)
from scripts.validate_skillpacks import build_live_capability_ids


def test_cofounder_assistant_spec_properties():
    """Verify COSA_COFOUNDER_ASSISTANT_AGENT_SPEC is configured with Solo Founder DNA."""
    spec = COSA_COFOUNDER_ASSISTANT_AGENT_SPEC
    assert spec.id == "cosa.agents.founder_assistant"
    assert spec.version == "1.0.0"
    assert spec.autonomy_level == AutonomyLevel.L0_OBSERVE
    assert "1 goal/week" in spec.instructions
    assert "Ship every Friday" in spec.instructions
    assert "Build" in spec.instructions and "Market/Sell" in spec.instructions
    assert "runway" in spec.instructions
    assert spec.prompt_ref.spec_id == "cosa.agents.founder_assistant.prompt"
    assert spec.metadata.get("role") == "founder_assistant"


def test_agent_profile_specs_mapping():
    """Verify AGENT_PROFILE_SPECS explicitly maps founder_assistant and cto."""
    assert AGENT_PROFILE_SPECS["founder_assistant"] is COSA_COFOUNDER_ASSISTANT_AGENT_SPEC
    assert AGENT_PROFILE_SPECS["cto"] is COSA_EXECUTIVE_CTO_AGENT_SPEC
    assert AGENT_PROFILE_SPECS["operations"].id == "cosa.agents.operations"


def test_cto_advisor_spec_properties():
    """Verify COSA_EXECUTIVE_CTO_AGENT_SPEC incorporates Startup CTO & Stage-Adaptive principles."""
    spec = COSA_EXECUTIVE_CTO_AGENT_SPEC
    assert spec.id == "cosa.executive.cto"
    assert spec.version == "1.1.0"
    assert spec.autonomy_level == AutonomyLevel.L1_PROPOSE
    assert "Stage-Adaptive CTO" in spec.instructions
    assert "Boring Technology" in spec.instructions
    assert "Monolith" in spec.instructions
    assert "Due Diligence" in spec.instructions

    # Verify pinned skill
    pinned_ids = [s.skill_id for s in spec.pinned_skills]
    assert "executive.cto-advisor" in pinned_ids


def test_marketing_spec_pins_bootstrapped_engine():
    """Verify COSA_MARKETING_AGENT_SPEC pins growth.bootstrapped-engine and deep-research 1.2.0."""
    pinned_ids = {s.skill_id: s.version for s in COSA_MARKETING_AGENT_SPEC.pinned_skills}
    assert "growth.bootstrapped-engine" in pinned_ids
    assert pinned_ids["growth.bootstrapped-engine"] == "1.0.0"
    assert "research.deep-research" in pinned_ids
    assert pinned_ids["research.deep-research"] == "1.2.0"


def test_workforce_catalog_suggested_personas():
    """Verify suggested personas in workforce catalog include Growth Marketer and Solo Founder."""
    campaign_planner = FUNCTIONAL_AGENT_CATALOG["campaign_planner"]
    assert "Growth Marketer" in campaign_planner.suggested_personas

    market_research = FUNCTIONAL_AGENT_CATALOG["market_research_specialist"]
    assert "Growth Marketer" in market_research.suggested_personas

    founder_orchestrator = FUNCTIONAL_AGENT_CATALOG["founder_office_orchestrator"]
    assert "Solo Founder" in founder_orchestrator.suggested_personas


@pytest.mark.asyncio
async def test_resolve_new_persona_pinned_skills():
    """Verify that all pinned skills for cofounder, cto, and marketing resolve cleanly."""
    repo = InMemorySpecRegistryRepository()
    caps = build_live_capability_ids()
    await seed_builtin_skillpacks(repo, capability_ids=caps)

    resolver = SkillResolver(repo)

    # 1. founder_assistant pinned skills resolve
    resolved_fa = await resolver.resolve(COSA_COFOUNDER_ASSISTANT_AGENT_SPEC.pinned_skills)
    assert len(resolved_fa) == len(COSA_COFOUNDER_ASSISTANT_AGENT_SPEC.pinned_skills)

    # 2. cto pinned skills resolve
    resolved_cto = await resolver.resolve(COSA_EXECUTIVE_CTO_AGENT_SPEC.pinned_skills)
    assert len(resolved_cto) == len(COSA_EXECUTIVE_CTO_AGENT_SPEC.pinned_skills)
    assert resolved_cto[0].id == "executive.cto-advisor"

    # 3. marketing pinned skills resolve
    resolved_mkt = await resolver.resolve(COSA_MARKETING_AGENT_SPEC.pinned_skills)
    assert any(s.id == "growth.bootstrapped-engine" for s in resolved_mkt)
