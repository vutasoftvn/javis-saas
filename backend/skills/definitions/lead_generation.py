"""
Lead Generation Skill Definition
"""
import os
from typing import List
from skills.base import BaseSkill, SkillDefinition


class LeadGenerationSkill(BaseSkill):
    def __init__(self):
        md_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "markdowns", "lead_generation.md")
        self.definition = SkillDefinition(
            id="lead-generation",
            name="Tìm kiếm & Thẩm định B2B Leads",
            domain="sales",
            description="Định nghĩa tiêu chuẩn ICP, chấm điểm Lead Scoring và soạn thảo kịch bản Cold Outreach",
            instruction_path=md_path,
            required_tools=["crm.search_leads", "crm.create_lead"],
            version="1.0.0"
        )

    async def load_instructions(self) -> str:
        if self.definition.instruction_path and os.path.exists(self.definition.instruction_path):
            with open(self.definition.instruction_path, "r", encoding="utf-8") as f:
                return f.read()
        return "Hướng dẫn tìm kiếm và chấm điểm Leads."

    def validate_prerequisites(self, available_tools: List[str]) -> bool:
        return all(t in available_tools for t in self.definition.required_tools)
