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

        # Marketing Domain
        "marketing:data": CapabilityRoute(domain="marketing", capability="data", tool_id="marketing.funnel.read", default_policy="L0_READ", handler_name="handle_marketing_data"),
        "marketing:research": CapabilityRoute(domain="marketing", capability="research", default_policy="L1_SUGGEST", handler_name="handle_marketing_research"),
        "marketing:reasoning": CapabilityRoute(domain="marketing", capability="reasoning", default_policy="L1_SUGGEST", handler_name="handle_marketing_reasoning"),
        "marketing:communication": CapabilityRoute(domain="marketing", capability="communication", default_policy="L2_DRAFT", handler_name="handle_marketing_communication"),
        "marketing:action": CapabilityRoute(domain="marketing", capability="action", tool_id="marketing.campaign.launch_draft", default_policy="L2_DRAFT", handler_name="handle_marketing_action"),
        "marketing:evaluation": CapabilityRoute(domain="marketing", capability="evaluation", default_policy="L1_SUGGEST", handler_name="handle_marketing_evaluation"),

        # Learning Domain
        "learning:data": CapabilityRoute(domain="learning", capability="data", tool_id="learning.lessons.read", default_policy="L0_READ", handler_name="handle_learning_data"),
        "learning:research": CapabilityRoute(domain="learning", capability="research", default_policy="L0_READ", handler_name="handle_learning_research"),
        "learning:reasoning": CapabilityRoute(domain="learning", capability="reasoning", default_policy="L1_SUGGEST", handler_name="handle_learning_reasoning"),
        "learning:communication": CapabilityRoute(domain="learning", capability="communication", default_policy="L1_SUGGEST", handler_name="handle_learning_communication"),
        "learning:action": CapabilityRoute(domain="learning", capability="action", tool_id="learning.lesson.create", default_policy="L2_DRAFT", handler_name="handle_learning_action"),
        "learning:evaluation": CapabilityRoute(domain="learning", capability="evaluation", default_policy="L1_SUGGEST", handler_name="handle_learning_evaluation"),

        # Legal Domain (Hard-capped at L1_SUGGEST / L2_DRAFT, no L3/L3A)
        "legal:data": CapabilityRoute(domain="legal", capability="data", tool_id="legal.checklist.read", default_policy="L0_READ", handler_name="handle_legal_data"),
        "legal:research": CapabilityRoute(domain="legal", capability="research", default_policy="L0_READ", handler_name="handle_legal_research"),
        "legal:reasoning": CapabilityRoute(domain="legal", capability="reasoning", default_policy="L1_SUGGEST", handler_name="handle_legal_reasoning"),
        "legal:communication": CapabilityRoute(domain="legal", capability="communication", default_policy="L2_DRAFT", handler_name="handle_legal_communication"),
        "legal:action": CapabilityRoute(domain="legal", capability="action", tool_id="legal.checklist.draft", default_policy="L2_DRAFT", handler_name="handle_legal_action"),
        "legal:evaluation": CapabilityRoute(domain="legal", capability="evaluation", default_policy="L1_SUGGEST", handler_name="handle_legal_evaluation"),

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
            route = cls._ROUTES[key]
            # Safety enforcement for Legal domain (§37)
            if domain.lower() == "legal" and route.default_policy in ("L3_EXECUTE", "L3A_EXECUTE_WITH_APPROVAL"):
                return CapabilityRoute(
                    domain=route.domain,
                    capability=route.capability,
                    tool_id=route.tool_id,
                    default_policy="L2_DRAFT",
                    handler_name=route.handler_name,
                )
            return route

        default_policy = "L2_DRAFT" if domain.lower() == "legal" else "L1_SUGGEST"
        return CapabilityRoute(
            domain=domain,
            capability=capability,
            default_policy=default_policy,
            handler_name="handle_generic_capability",
        )
