"""Helper test: dựng pin advisor (deployment + overlay) thật từ catalog và seed registry."""

from __future__ import annotations

from pathlib import Path

from agent.executive_board.models import (
    AdvisorOverlayPin,
    PinnedSkillIdentity,
    ProjectDeploymentPin,
    SelectedAdvisorExecutionPin,
)
from agent.registry.publisher import publish_skill_spec
from agent.registry.repository import SpecRegistryRepository

from apps.cosa.agents.catalog import CATALOG_BY_PROFILE
from apps.cosa.agents.executive_advisor_overlays_generated import ADVISOR_OVERLAY_CATALOG
from apps.cosa.agents.executive_advisor_roles_generated import EXECUTIVE_ROLE_CATALOG
from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

SKILLPACKS = Path(__file__).resolve().parents[3] / "skillpacks"


def build_pin(role_key: str, *, deployment_id: str = "dep-1") -> SelectedAdvisorExecutionPin:
    overlay = ADVISOR_OVERLAY_CATALOG[role_key]
    profile = CATALOG_BY_PROFILE[overlay.required_profile_key].agent_spec
    return SelectedAdvisorExecutionPin(
        role_key=role_key,
        deployment=ProjectDeploymentPin(
            project_agent_deployment_id=deployment_id,
            profile_key=overlay.required_profile_key,
            spec_id=profile.id,
            spec_version=profile.version,
            spec_hash=profile.compute_hash(),
        ),
        overlay=AdvisorOverlayPin(
            role_key=role_key,
            overlay_spec_id=overlay.overlay_spec_id,
            overlay_spec_version=overlay.overlay_spec_version,
            overlay_spec_hash=overlay.overlay_definition_hash,
            skill_pins=tuple(
                PinnedSkillIdentity(
                    skill_id=p.skill_id, version=p.version, definition_hash=p.definition_hash
                )
                for p in overlay.skill_pins
            ),
        ),
    )


async def seed_advisor_registry(registry: SpecRegistryRepository, role_key: str) -> None:
    """Publish skill thật của role + toàn bộ prompt/model policy/AgentSpec built-in."""
    for ref in EXECUTIVE_ROLE_CATALOG[role_key].required_skill_pins:
        path = ref[len("skillpack:") :].partition("@")[0]
        await publish_skill_spec(
            parse_skillpack_spec(SKILLPACKS / path), repository=registry, publisher="test"
        )
    await seed_cosa_agent_specs(registry)
