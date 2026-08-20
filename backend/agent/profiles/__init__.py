"""
COSA Agent Profiles Package
"""
from agent.profiles.definitions import (
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
from agent.profiles.registry import (
    AgentProfileRegistry,
    agent_profile_registry,
    register_all_workforce_profiles,
)
from agent.profiles.schema import AgentProfile, AgentProfileRegistryInterface

__all__ = [
    "AgentProfile",
    "AgentProfileRegistry",
    "AgentProfileRegistryInterface",
    "agent_profile_registry",
    "get_cofounder_profile",
    "get_customer_success_profile",
    "get_finance_profile",
    "get_growth_profile",
    "get_hr_profile",
    "get_legal_profile",
    "get_marketing_profile",
    "get_operations_profile",
    "get_product_profile",
    "get_research_profile",
    "get_sales_profile",
    "get_tech_profile",
    "register_all_workforce_profiles",
]
