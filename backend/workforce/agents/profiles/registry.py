"""
COSA Central Agent Profile Registry
Quản lý và tra cứu hồ sơ 12 vai trò Agent khai báo trong Workforce (Structure.md Mục 8, 37).
"""
from typing import Dict, List, Optional
from agent_runtime.profiles.definitions import (
    get_cofounder_profile,
    get_customer_success_profile,
    get_finance_profile,
    get_growth_profile,
    get_hr_profile,
    get_legal_profile,
    get_marketing_profile,
    get_operations_profile,
    get_product_profile,
    get_research_profile,
    get_sales_profile,
    get_tech_profile,
)
from workforce.agents.profiles.schemas import AgentProfile, AgentProfileRegistryInterface


class AgentProfileRegistry(AgentProfileRegistryInterface):
    """Kho quản lý danh mục hồ sơ 12 Agent chuyên sâu trong COSA Workforce"""

    def __init__(self):
        self._profiles: Dict[str, AgentProfile] = {}

    async def get_profile(self, profile_id: str) -> Optional[AgentProfile]:
        """Truy xuất hồ sơ Agent theo mã định danh duy nhất"""
        return self._profiles.get(profile_id)

    async def list_profiles(self) -> List[AgentProfile]:
        """Lấy danh sách toàn bộ hồ sơ vai trò"""
        return list(self._profiles.values())

    async def register_profile(self, profile: AgentProfile) -> bool:
        """Đăng ký hồ sơ vai trò mới"""
        self._profiles[profile.id] = profile
        return True


# Singleton instance
agent_profile_registry = AgentProfileRegistry()

# Tự động nạp toàn bộ 12 Standard Workforce Profiles
def register_all_workforce_profiles(registry: AgentProfileRegistry = agent_profile_registry) -> None:
    workforce = [
        get_cofounder_profile(),
        get_marketing_profile(),
        get_sales_profile(),
        get_finance_profile(),
        get_legal_profile(),
        get_research_profile(),
        get_product_profile(),
        get_tech_profile(),
        get_operations_profile(),
        get_hr_profile(),
        get_growth_profile(),
        get_customer_success_profile(),
    ]
    for p in workforce:
        registry._profiles[p.id] = p


register_all_workforce_profiles()
