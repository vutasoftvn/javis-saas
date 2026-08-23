# backend/agentos/skills/instruction_loader.py
from __future__ import annotations

from agentos.skills.loader import load_skill_instructions
from agentos.skills.registry import SkillRegistry


class SkillInstructionLoader:
    """Level 1 progressive disclosure (blueprint §24): only reads a skill's
    SKILL.md when explicitly requested for a selected skill — registry
    discovery (Level 0) never reads instruction bodies.
    """

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    def load(self, skill_id: str) -> str:
        record = self._registry.get(skill_id)
        return load_skill_instructions(record.skill_dir)
