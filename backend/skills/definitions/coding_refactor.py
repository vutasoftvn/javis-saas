"""
Clean Architecture & BuildSpec Coding Skill Definition
"""
import os
from typing import List
from skills.base import BaseSkill, SkillDefinition


class CodingRefactorSkill(BaseSkill):
    def __init__(self):
        md_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "markdowns", "coding_refactor.md")
        self.definition = SkillDefinition(
            id="coding-refactor",
            name="Clean Architecture & BuildSpec",
            domain="coding",
            description="Tách rời Business Core độc lập với AI, thiết lập Interfaces và soạn thảo BuildSpec",
            instruction_path=md_path,
            required_tools=["filesystem.read", "filesystem.write"],
            version="1.0.0"
        )

    async def load_instructions(self) -> str:
        if self.definition.instruction_path and os.path.exists(self.definition.instruction_path):
            with open(self.definition.instruction_path, "r", encoding="utf-8") as f:
                return f.read()
        return "Hướng dẫn lập trình Clean Architecture."

    def validate_prerequisites(self, available_tools: List[str]) -> bool:
        return all(t in available_tools for t in self.definition.required_tools)
