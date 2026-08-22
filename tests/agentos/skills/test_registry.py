# backend/tests/agentos/skills/test_registry.py
from pathlib import Path

import pytest
import yaml

from agentos.skills.manifest import SkillLifecycleStatus
from agentos.skills.registry import SkillNotFoundError, SkillRegistry


def _write_skill(root: Path, skill_id: str) -> Path:
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
    (skill_dir / "SKILL.md").write_text("do it", encoding="utf-8")
    return skill_dir


def test_discover_registers_valid_skill_as_active(tmp_path: Path):
    _write_skill(tmp_path, "core.weekly-review")
    registry = SkillRegistry()

    discovered = registry.discover(tmp_path)

    assert discovered == ["core.weekly-review"]
    record = registry.get("core.weekly-review")
    assert record.status == SkillLifecycleStatus.ACTIVE
    assert record.manifest.metadata.id == "core.weekly-review"


def test_discover_skips_directory_with_broken_manifest(tmp_path: Path):
    broken_dir = tmp_path / "broken-skill"
    broken_dir.mkdir()
    (broken_dir / "manifest.yaml").write_text("not: [valid, manifest", encoding="utf-8")
    registry = SkillRegistry()

    discovered = registry.discover(tmp_path)

    assert discovered == []


def test_get_missing_skill_raises():
    registry = SkillRegistry()
    with pytest.raises(SkillNotFoundError):
        registry.get("missing")


def test_set_status_updates_record(tmp_path: Path):
    _write_skill(tmp_path, "core.weekly-review")
    registry = SkillRegistry()
    registry.discover(tmp_path)

    registry.set_status("core.weekly-review", SkillLifecycleStatus.DEPRECATED)

    assert registry.get("core.weekly-review").status == SkillLifecycleStatus.DEPRECATED


def test_list_filters_by_status(tmp_path: Path):
    _write_skill(tmp_path, "core.weekly-review")
    _write_skill(tmp_path, "core.daily-plan")
    registry = SkillRegistry()
    registry.discover(tmp_path)
    registry.set_status("core.daily-plan", SkillLifecycleStatus.DEPRECATED)

    active = registry.list(status=SkillLifecycleStatus.ACTIVE)

    assert [r.manifest.metadata.id for r in active] == ["core.weekly-review"]
