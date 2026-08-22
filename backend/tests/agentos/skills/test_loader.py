# backend/tests/agentos/skills/test_loader.py
from pathlib import Path

import pytest
import yaml

from agentos.skills.loader import SkillManifestError, load_skill_instructions, load_skill_manifest


def _write_valid_skill(skill_dir: Path) -> None:
    skill_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {"id": "core.weekly-review", "name": "Weekly Review", "version": "1.0.0", "description": "d"},
        "publisher": {"name": "internal", "type": "official"},
        "source": {"type": "local", "path": str(skill_dir)},
        "capability": {"domain": "core", "category": "review", "intents": ["weekly review"]},
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": False},
        "risk": {"level": "low"},
        "trust": {"tier": "T0", "security_scan": "passed"},
        "quality": {"eval_score": 0.9, "success_rate": 0.8},
    }
    (skill_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (skill_dir / "SKILL.md").write_text("# Weekly Review\n\nDo the weekly review.\n", encoding="utf-8")


def test_load_skill_manifest_parses_valid_manifest(tmp_path: Path):
    _write_valid_skill(tmp_path)
    manifest = load_skill_manifest(tmp_path)
    assert manifest.metadata.id == "core.weekly-review"


def test_load_skill_manifest_raises_when_manifest_missing(tmp_path: Path):
    with pytest.raises(SkillManifestError):
        load_skill_manifest(tmp_path)


def test_load_skill_instructions_reads_skill_md(tmp_path: Path):
    _write_valid_skill(tmp_path)
    instructions = load_skill_instructions(tmp_path)
    assert "Do the weekly review." in instructions


def test_load_skill_instructions_raises_when_missing(tmp_path: Path):
    tmp_path.mkdir(exist_ok=True)
    with pytest.raises(SkillManifestError):
        load_skill_instructions(tmp_path)
