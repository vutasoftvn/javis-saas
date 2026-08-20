"""
Market Research Skill Definition
"""
import os
from typing import List
from skills.base import BaseSkill, SkillDefinition


class MarketResearchSkill(BaseSkill):
    def __init__(self):
        md_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "markdowns", "market_research.md")
        self.definition = SkillDefinition(
            id="market-research",
            name="Nghiên cứu Thị trường & Định vị",
            domain="marketing",
            description="Phân tích quy mô thị trường (TAM/SAM/SOM), đối thủ và xây dựng ma trận định vị",
            instruction_path=md_path,
            required_tools=["web.search", "web.fetch"],
            version="1.0.0"
        )

    async def load_instructions(self) -> str:
        if self.definition.instruction_path and os.path.exists(self.definition.instruction_path):
            with open(self.definition.instruction_path, "r", encoding="utf-8") as f:
                return f.read()
        return "Hướng dẫn nghiên cứu thị trường và đối thủ."

    def validate_prerequisites(self, available_tools: List[str]) -> bool:
        return all(tool in available_tools for tool in self.definition.required_tools)
