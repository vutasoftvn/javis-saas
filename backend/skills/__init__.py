"""
COSA Skills Repository Package
"""
from skills.base import BaseSkill, SkillDefinition
from skills.definitions import (
    CodingRefactorSkill,
    LeadGenerationSkill,
    MarketResearchSkill,
    OKRSettingSkill,
    PMFDiscoverySkill,
    TT58AuditSkill,
)
from skills.repository import SkillRepository, register_all_standard_skills, skill_repository

__all__ = [
    "BaseSkill",
    "CodingRefactorSkill",
    "LeadGenerationSkill",
    "MarketResearchSkill",
    "OKRSettingSkill",
    "PMFDiscoverySkill",
    "SkillDefinition",
    "SkillRepository",
    "TT58AuditSkill",
    "register_all_standard_skills",
    "skill_repository",
]
