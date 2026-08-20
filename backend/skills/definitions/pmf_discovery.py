"""
PMF Discovery Skill Definition
"""
import os
from typing import List
from skills.base import BaseSkill, SkillDefinition


class PMFDiscoverySkill(BaseSkill):
    def __init__(self):
        md_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "markdowns", "pmf_discovery.md")
        self.definition = SkillDefinition(
            id="pmf-discovery",
            name="Kiểm chứng Product-Market Fit",
            domain="startup",
            description="Khung phỏng vấn JTBD, đo lường mức độ thất vọng (Sean Ellis Test) và Retention Cohort",
            instruction_path=md_path,
            required_tools=[],
            version="1.0.0"
        )

    async def load_instructions(self) -> str:
        if self.definition.instruction_path and os.path.exists(self.definition.instruction_path):
            with open(self.definition.instruction_path, "r", encoding="utf-8") as f:
                return f.read()
        return "Hướng dẫn kiểm chứng PMF."

    def validate_prerequisites(self, available_tools: List[str]) -> bool:
        return True
