from __future__ import annotations

from pathlib import Path
import pytest
import yaml

from agent.executive_board.models import ExecutiveBoardInputError
from agent.executive_board.skill_pins import parse_skill_pin_ref, resolve_role_pin_skills
from agent.registry.models import PublishedSpecRecord
from agent.registry.repository import InMemorySpecRegistryRepository
from apps.cosa.agents.executive_advisor_roles_generated import (
    EXECUTIVE_ROLE_CATALOG,
    EXECUTIVE_ROLE_KEYS,
)


def test_cto_role_contains_workspace_site_builder_skill_pin():
    assert "cto" in EXECUTIVE_ROLE_KEYS
    cto_def = EXECUTIVE_ROLE_CATALOG["cto"]
    assert cto_def.key == "cto"
    assert "skillpack:executive/cto-advisor@1.0.0" in cto_def.required_skill_pins
    assert "skillpack:engineering/workspace-site-builder@1.0.0" in cto_def.required_skill_pins
    assert len(cto_def.required_skill_pins) == 2


def test_parse_workspace_site_builder_skill_pin():
    skill_id, version = parse_skill_pin_ref("skillpack:engineering/workspace-site-builder@1.0.0")
    assert skill_id == "engineering.workspace-site-builder"
    assert version == "1.0.0"


def test_workspace_site_builder_manifest_contract():
    repo_root = Path(__file__).resolve().parents[3]
    manifest_path = repo_root / "skillpacks" / "engineering" / "workspace-site-builder" / "manifest.yaml"
    assert manifest_path.is_file(), f"Manifest not found at {manifest_path}"

    with open(manifest_path, encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    assert manifest["apiVersion"] == "agentos.ai/v1"
    assert manifest["kind"] == "Skill"
    assert manifest["metadata"]["id"] == "engineering.workspace-site-builder"
    assert manifest["metadata"]["version"] == "1.0.0"
    assert manifest["autonomy"]["ceiling"] == "L1_PROPOSE"
    assert manifest["autonomy"]["side_effect_class"] == "A"
    assert manifest["evidence"]["self_validation_forbidden"] is True
    assert manifest["quality"]["eval_suite"] == "evals/engineering/workspace-site-builder.yaml"
    assert "missing-workspace" in manifest["quality"]["required_negative_cases"]
    assert "cross-workspace" in manifest["quality"]["required_negative_cases"]
    assert "autonomous-deploy" in manifest["quality"]["required_negative_cases"]


def test_workspace_site_builder_references_exist():
    repo_root = Path(__file__).resolve().parents[3]
    ref_dir = repo_root / "skillpacks" / "engineering" / "workspace-site-builder" / "references"
    expected_refs = [
        "sandbox_isolation_guide.md",
        "site_and_block_specifications.md",
        "form_survey_engine_spec.md",
        "ecommerce_checkout_integration.md",
    ]
    for ref_name in expected_refs:
        ref_file = ref_dir / ref_name
        assert ref_file.is_file(), f"Reference file {ref_name} missing at {ref_file}"
        assert ref_file.stat().st_size > 500, f"Reference file {ref_name} is unexpectedly empty"


@pytest.mark.asyncio
async def test_resolve_workspace_site_builder_skill_pin_success():
    registry = InMemorySpecRegistryRepository()
    await registry.publish(
        PublishedSpecRecord(
            spec_kind="skill",
            spec_id="engineering.workspace-site-builder",
            version="1.0.0",
            definition_hash="hash-ws-site-builder-100",
            content={"id": "engineering.workspace-site-builder", "version": "1.0.0"},
            publisher="cosa_built_in",
        )
    )

    refs = await resolve_role_pin_skills(
        ("skillpack:engineering/workspace-site-builder@1.0.0",),
        registry,
    )
    assert len(refs) == 1
    assert refs[0].skill_id == "engineering.workspace-site-builder"
    assert refs[0].version == "1.0.0"
    assert refs[0].definition_hash == "hash-ws-site-builder-100"
