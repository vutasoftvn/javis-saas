from pathlib import Path

import yaml

from agentos.skills.manifest import TrustTier
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import SkillRouter
from agentos.skills.supply_chain.artifact_store import ImmutableArtifactStore
from agentos.skills.supply_chain.catalog import ExternalSkillCandidate
from agentos.skills.supply_chain.pipeline import SupplyChainPipeline


def _write_external_skill(
    root: Path, skill_id: str, *, commit: str = "4bc9a82c1234567890abcdef1234567890abcdef"
) -> Path:
    skill_dir = root / skill_id.replace(".", "-")
    skill_dir.mkdir(parents=True)
    manifest = {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {"id": skill_id, "name": skill_id, "version": "1.0.0", "description": "d"},
        "publisher": {"name": "community", "type": "community"},
        "source": {
            "type": "git",
            "path": f"skills/{skill_id}",
            "repository": "https://github.com/example/skills",
            "commit": commit,
        },
        "capability": {"domain": "core", "category": "general", "intents": ["faq writer", "write faq answers"]},
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": False},
        "risk": {"level": "low"},
        "trust": {"tier": "T0", "security_scan": "pending"},
        "quality": {"eval_score": 0.6, "success_rate": 0.6},
    }
    (skill_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(f"# {skill_id}\n\nWrite FAQ answers.\n", encoding="utf-8")
    return skill_dir


def test_router_never_selects_a_skill_before_it_is_promoted_to_active(tmp_path: Path):
    skill_dir = _write_external_skill(tmp_path / "source", "community.faq-writer")
    registry = SkillRegistry()
    artifact_store = ImmutableArtifactStore(tmp_path / "registry" / "skills")
    pipeline = SupplyChainPipeline(registry, artifact_store)
    router = SkillRouter(registry)
    candidate = ExternalSkillCandidate(
        id="community.faq-writer",
        name="FAQ Writer",
        description="d",
        repository="https://github.com/example/skills",
        path="skills/community.faq-writer",
        commit="4bc9a82c1234567890abcdef1234567890abcdef",
    )
    skill_id = pipeline.import_candidate(candidate, skill_dir)

    assert router.select("write faq answers") is None  # IMPORTED

    pipeline.scan(skill_id)
    assert router.select("write faq answers") is None  # VERIFIED

    pipeline.stage(skill_id)
    assert router.select("write faq answers") is None  # STAGED

    pipeline.promote_to_active(skill_id, approved_by="founder")
    selected = router.select("write faq answers")
    assert selected is not None
    assert selected.metadata.id == "community.faq-writer"


def test_router_never_selects_a_quarantined_skill(tmp_path: Path):
    skill_dir = _write_external_skill(tmp_path / "source", "community.risky-writer")
    manifest_path = skill_dir / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["permissions"]["business_write"] = True
    manifest["trust"]["tier"] = "T3"
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    registry = SkillRegistry()
    artifact_store = ImmutableArtifactStore(tmp_path / "registry" / "skills")
    pipeline = SupplyChainPipeline(registry, artifact_store)
    router = SkillRouter(registry, min_trust=TrustTier.T2)
    candidate = ExternalSkillCandidate(
        id="community.risky-writer",
        name="Risky Writer",
        description="d",
        repository="https://github.com/example/skills",
        path="skills/community.risky-writer",
        commit="4bc9a82c1234567890abcdef1234567890abcdef",
    )
    skill_id = pipeline.import_candidate(candidate, skill_dir)
    result = pipeline.scan(skill_id)

    assert result.passed is False
    assert router.select("write faq answers") is None
