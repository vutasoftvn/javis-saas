from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel


class CapabilityRoute(BaseModel):
    domain: str
    capability: str
    tool_id: Optional[str] = None
    default_policy: str = "L0_READ"
    handler_name: str


class DomainCapabilityRouter:
    """Routes plan steps to domain handlers, shared capabilities, and underlying tool adapters."""

    _ROUTES: Dict[str, CapabilityRoute] = {
        # Sales Domain
        "sales:data": CapabilityRoute(domain="sales", capability="data", tool_id="sales.pipeline.read", default_policy="L0_READ", handler_name="handle_sales_data"),
        "sales:research": CapabilityRoute(domain="sales", capability="research", tool_id="web.search", default_policy="L1_SUGGEST", handler_name="handle_sales_research"),
        "sales:reasoning": CapabilityRoute(domain="sales", capability="reasoning", default_policy="L1_SUGGEST", handler_name="handle_sales_reasoning"),
        "sales:communication": CapabilityRoute(domain="sales", capability="communication", default_policy="L2_DRAFT", handler_name="handle_sales_communication"),
        "sales:action": CapabilityRoute(domain="sales", capability="action", tool_id="n8n.sales.outreach_dispatch", default_policy="L3A_EXECUTE_WITH_APPROVAL", handler_name="handle_sales_action"),
        "sales:evaluation": CapabilityRoute(domain="sales", capability="evaluation", default_policy="L1_SUGGEST", handler_name="handle_sales_evaluation"),

        # Finance Domain
        "finance:data": CapabilityRoute(domain="finance", capability="data", tool_id="finance.ledger.read", default_policy="L0_READ", handler_name="handle_finance_data"),
        "finance:reasoning": CapabilityRoute(domain="finance", capability="reasoning", default_policy="L1_SUGGEST", handler_name="handle_finance_reasoning"),
        "finance:research": CapabilityRoute(domain="finance", capability="research", default_policy="L1_SUGGEST", handler_name="handle_finance_research"),
        "finance:action": CapabilityRoute(domain="finance", capability="action", tool_id="finance.accounting.review_draft", default_policy="L2_DRAFT", handler_name="handle_finance_action"),
        "finance:evaluation": CapabilityRoute(domain="finance", capability="evaluation", default_policy="L1_SUGGEST", handler_name="handle_finance_evaluation"),

        # Founder / Chief of Staff Domain
        "founder:research": CapabilityRoute(domain="founder", capability="research", default_policy="L0_READ", handler_name="handle_founder_research"),
        "founder:reasoning": CapabilityRoute(domain="founder", capability="reasoning", default_policy="L1_SUGGEST", handler_name="handle_founder_reasoning"),
        "founder:action": CapabilityRoute(domain="founder", capability="action", default_policy="L2_DRAFT", handler_name="handle_founder_action"),
        "founder:evaluation": CapabilityRoute(domain="founder", capability="evaluation", default_policy="L1_SUGGEST", handler_name="handle_founder_evaluation"),
    }

    @classmethod
    def resolve_route(cls, domain: str, capability: str) -> CapabilityRoute:
        key = f"{domain.lower()}:{capability.lower()}"
        if key in cls._ROUTES:
            return cls._ROUTES[key]
        return CapabilityRoute(
            domain=domain,
            capability=capability,
            default_policy="L1_SUGGEST",
            handler_name="handle_generic_capability",
        )
