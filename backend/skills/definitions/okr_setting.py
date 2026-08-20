"""
OKR & 12 Week Year Management Skill Definition
"""
import os
from typing import List
from skills.base import BaseSkill, SkillDefinition


class OKRSettingSkill(BaseSkill):
    def __init__(self):
        md_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "markdowns", "okr_setting.md")
        self.definition = SkillDefinition(
            id="okr-setting",
            name="Thiết lập Mục tiêu OKR & Kế hoạch 12 Tuần",
            domain="management",
            description="Xác lập Objectives và Key Results định lượng, phân rã kế hoạch hành động 12 Week Year",
            instruction_path=md_path,
            required_tools=[],
            version="1.0.0"
        )

    async def load_instructions(self) -> str:
        if self.definition.instruction_path and os.path.exists(self.definition.instruction_path):
            with open(self.definition.instruction_path, "r", encoding="utf-8") as f:
                return f.read()
        return "Hướng dẫn thiết lập OKR."

    def validate_prerequisites(self, available_tools: List[str]) -> bool:
        return True
