"""
COSA 12 Agent Profiles Definitions Package
"""
from agent.profiles.definitions.cofounder import get_cofounder_profile
from agent.profiles.definitions.marketing import (
    get_finance_profile,
    get_legal_profile,
    get_marketing_profile,
    get_research_profile,
    get_sales_profile,
)
from agent.profiles.definitions.product import (
    get_customer_success_profile,
    get_growth_profile,
    get_hr_profile,
    get_operations_profile,
    get_product_profile,
    get_tech_profile,
)

__all__ = [
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
]
