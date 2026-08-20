"""
TT58 Financial Audit Skill Definition
"""
import os
from typing import List
from skills.base import BaseSkill, SkillDefinition


class TT58AuditSkill(BaseSkill):
    def __init__(self):
        md_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "markdowns", "tt58_audit.md")
        self.definition = SkillDefinition(
            id="tt58-audit",
            name="Kiểm toán & Kế toán Doanh nghiệp TT58",
            domain="finance",
            description="Định khoản kế toán theo TT58, tính toán biên lợi nhuận, phân bổ chi phí và tính Runway",
            instruction_path=md_path,
            required_tools=["finance.query_pnl", "finance.calculate_runway"],
            version="1.0.0"
        )

    async def load_instructions(self) -> str:
        if self.definition.instruction_path and os.path.exists(self.definition.instruction_path):
            with open(self.definition.instruction_path, "r", encoding="utf-8") as f:
                return f.read()
        return "Hướng dẫn kế toán và kiểm soát tài chính TT58."

    def validate_prerequisites(self, available_tools: List[str]) -> bool:
        return all(t in available_tools for t in self.definition.required_tools)
