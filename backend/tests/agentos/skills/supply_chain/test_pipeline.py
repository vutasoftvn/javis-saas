from pathlib import Path

import pytest
import yaml

from agentos.skills.manifest import SkillLifecycleStatus
from agentos.skills.registry import SkillRegistry
from agentos.skills.supply_chain.artifact_store import ImmutableArtifactStore
from agentos.skills.supply_chain.catalog import ExternalSkillCandidate
from agentos.skills.supply_chain.lifecycle import InvalidSkillLifecycleTransition
from agentos.skills.supply_chain.pinning import UnpinnedSkillSourceError
from agentos.skills.supply_chain.pipeline import ApprovalRequiredError, SupplyChainPipeline


def _write_external_skill(
    root: Path,
    skill_id: str,
    *,
    commit: str = "4bc9a82c1234567890abcdef1234567890abcdef",
    business_write: bool = False,
    tier: str = "T0",
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
        "capability": {"domain": "core", "category": "general", "intents": [skill_id]},
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": business_write},
        "risk": {"level": "low"},
        "trust": {"tier": tier, "security_scan": "pending"},
        "quality": {"eval_score": 0.5, "success_rate": 0.5},
    }
    (skill_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(f"# {skill_id}\n\nDo it.\n", encoding="utf-8")
    return skill_dir


def _candidate(skill_id: str, commit: str | None = "4bc9a82c1234567890abcdef1234567890abcdef") -> ExternalSkillCandidate:
    return ExternalSkillCandidate(
        id=skill_id,
        name=skill_id,
        description="d",
        repository="https://github.com/example/skills",
        path=f"skills/{skill_id}",
        commit=commit,
    )


def _make_pipeline(tmp_path: Path) -> tuple[SupplyChainPipeline, SkillRegistry]:
    registry = SkillRegistry()
    artifact_store = ImmutableArtifactStore(tmp_path / "registry" / "skills")
    return SupplyChainPipeline(registry, artifact_store), registry


def test_happy_path_imports_scans_stages_and_activates(tmp_path: Path):
    skill_dir = _write_external_skill(tmp_path / "source", "community.faq-writer")
    pipeline, registry = _make_pipeline(tmp_path)

    skill_id = pipeline.import_candidate(_candidate("community.faq-writer"), skill_dir)
    assert registry.get(skill_id).status == SkillLifecycleStatus.IMPORTED

    result = pipeline.scan(skill_id)
    assert result.passed is True
    assert registry.get(skill_id).status == SkillLifecycleStatus.VERIFIED

    artifact_dir = pipeline.stage(skill_id)
    assert artifact_dir.exists()
    assert registry.get(skill_id).status == SkillLifecycleStatus.STAGED

    pipeline.promote_to_active(skill_id, approved_by="founder")
    assert registry.get(skill_id).status == SkillLifecycleStatus.ACTIVE


def test_scan_failure_quarantines_instead_of_verifying(tmp_path: Path):
    skill_dir = _write_external_skill(
        tmp_path / "source", "community.risky-writer", business_write=True, tier="T3"
    )
    pipeline, registry = _make_pipeline(tmp_path)
    skill_id = pipeline.import_candidate(_candidate("community.risky-writer"), skill_dir)

    result = pipeline.scan(skill_id)

    assert result.passed is False
    assert registry.get(skill_id).status == SkillLifecycleStatus.QUARANTINED


def test_promote_without_approver_raises(tmp_path: Path):
    skill_dir = _write_external_skill(tmp_path / "source", "community.faq-writer")
    pipeline, _ = _make_pipeline(tmp_path)
    skill_id = pipeline.import_candidate(_candidate("community.faq-writer"), skill_dir)
    pipeline.scan(skill_id)
    pipeline.stage(skill_id)

    with pytest.raises(ApprovalRequiredError):
        pipeline.promote_to_active(skill_id, approved_by="")


def test_cannot_skip_stages_straight_to_active(tmp_path: Path):
    skill_dir = _write_external_skill(tmp_path / "source", "community.faq-writer")
    pipeline, _ = _make_pipeline(tmp_path)
    skill_id = pipeline.import_candidate(_candidate("community.faq-writer"), skill_dir)

    with pytest.raises(InvalidSkillLifecycleTransition):
        pipeline.promote_to_active(skill_id, approved_by="founder")


def test_import_rejects_unpinned_candidate(tmp_path: Path):
    skill_dir = _write_external_skill(tmp_path / "source", "community.faq-writer")
    pipeline, _ = _make_pipeline(tmp_path)

    with pytest.raises(UnpinnedSkillSourceError):
        pipeline.import_candidate(_candidate("community.faq-writer", commit=None), skill_dir)


def test_stage_rejects_manifest_missing_commit(tmp_path: Path):
    skill_dir = _write_external_skill(tmp_path / "source", "community.faq-writer")
    # Overwrite the manifest's own source.commit to simulate a manifest that
    # was hand-edited after import to drop its pin.
    manifest_path = skill_dir / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["source"]["commit"] = None
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    pipeline, _ = _make_pipeline(tmp_path)
    skill_id = pipeline.import_candidate(_candidate("community.faq-writer"), skill_dir)
    pipeline.scan(skill_id)

    with pytest.raises(UnpinnedSkillSourceError):
        pipeline.stage(skill_id)
