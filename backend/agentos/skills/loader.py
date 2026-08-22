# backend/agentos/skills/loader.py
from __future__ import annotations

from pathlib import Path

import yaml

from agentos.skills.manifest import SkillManifest

MANIFEST_FILENAME = "manifest.yaml"
INSTRUCTIONS_FILENAME = "SKILL.md"


class SkillManifestError(Exception):
    def __init__(self, skill_dir: Path, reason: str) -> None:
        super().__init__(f"Invalid skill at {skill_dir}: {reason}")
        self.skill_dir = skill_dir


def load_skill_manifest(skill_dir: Path) -> SkillManifest:
    manifest_path = skill_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise SkillManifestError(skill_dir, f"missing {MANIFEST_FILENAME}")
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    try:
        return SkillManifest(**raw)
    except Exception as exc:
        raise SkillManifestError(skill_dir, str(exc)) from exc


def load_skill_instructions(skill_dir: Path) -> str:
    instructions_path = skill_dir / INSTRUCTIONS_FILENAME
    if not instructions_path.is_file():
        raise SkillManifestError(skill_dir, f"missing {INSTRUCTIONS_FILENAME}")
    return instructions_path.read_text(encoding="utf-8")
