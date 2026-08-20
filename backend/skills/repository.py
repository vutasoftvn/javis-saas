"""
COSA Central Skills Repository
Quản lý đăng ký, tra cứu và nạp hướng dẫn kỹ năng (Structure.md Mục 9).
"""
from typing import Dict, List, Optional
from skills.base import BaseSkill
from skills.definitions import (
    CodingRefactorSkill,
    LeadGenerationSkill,
    MarketResearchSkill,
    OKRSettingSkill,
    PMFDiscoverySkill,
    TT58AuditSkill,
)


class SkillRepository:
    """Kho lưu trữ và quản lý kỹ năng nghiệp vụ tập trung của COSA"""

    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """Đăng ký một kỹ năng vào kho"""
        self._skills[skill.definition.id] = skill

    def get(self, skill_id: str) -> Optional[BaseSkill]:
        """Truy xuất kỹ năng theo mã định danh duy nhất"""
        return self._skills.get(skill_id)

    def list_skills(self, domain: Optional[str] = None) -> List[BaseSkill]:
        """Lấy danh sách kỹ năng (có thể lọc theo domain)"""
        if not domain:
            return list(self._skills.values())
        return [s for s in self._skills.values() if s.definition.domain == domain]

    def validate_prerequisites(self, skill_id: str, available_tools: List[str]) -> bool:
        """Kiểm tra xem Runtime có đủ Tools cần thiết để áp dụng Skill này hay không"""
        skill = self.get(skill_id)
        if not skill:
            return False
        return skill.validate_prerequisites(available_tools)


# Singleton instance
skill_repository = SkillRepository()

# Tự động đăng ký 6 standard skills
def register_all_standard_skills(repository: SkillRepository = skill_repository) -> None:
    standard_skills = [
        MarketResearchSkill(),
        PMFDiscoverySkill(),
        LeadGenerationSkill(),
        TT58AuditSkill(),
        OKRSettingSkill(),
        CodingRefactorSkill(),
    ]
    for s in standard_skills:
        repository.register(s)


register_all_standard_skills()
