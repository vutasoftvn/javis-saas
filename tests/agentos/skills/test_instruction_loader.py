# backend/tests/agentos/skills/test_instruction_loader.py
from pathlib import Path

import pytest
import yaml

from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.registry import SkillNotFoundError, SkillRegistry


def _write_skill(root: Path, skill_id: str, instructions: str) -> None:
    skill_dir = root / skill_id.replace(".", "-")
    skill_dir.mkdir(parents=True)
    manifest = {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {"id": skill_id, "name": skill_id, "version": "1.0.0", "description": "d"},
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
    (skill_dir / "SKILL.md").write_text(instructions, encoding="utf-8")


def test_load_returns_skill_md_contents(tmp_path: Path):
    _write_skill(tmp_path, "core.weekly-review", "# Weekly Review\n\nStep 1: reflect.\n")
    registry = SkillRegistry()
    registry.discover(tmp_path)
    loader = SkillInstructionLoader(registry)

    instructions = loader.load("core.weekly-review")

    assert "Step 1: reflect." in instructions


def test_load_raises_for_unregistered_skill():
    registry = SkillRegistry()
    loader = SkillInstructionLoader(registry)

    with pytest.raises(SkillNotFoundError):
        loader.load("missing")
