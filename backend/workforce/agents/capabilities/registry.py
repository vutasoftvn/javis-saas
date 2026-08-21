"""Static registry and taxonomy for capabilities within COSA OS.

Maps capability identifiers (format: `domain.resource.action`) to risk levels (L0-L5),
corresponding permission levels, and approval requirements.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from workforce.agents.governance.policy_engine import PermissionLevel


class RiskLevel(str, Enum):
    L0_PUBLIC_READ = "L0"       # Public, non-sensitive read
    L1_INTERNAL_READ = "L1"     # Workspace internal read
    L2_DRAFT_WRITE = "L2"       # Low-risk write / local draft
    L3_OPERATIONAL_WRITE = "L3" # Standard internal write / operational
    L4_EXTERNAL_SIDE_EFFECT = "L4" # External side-effect (e.g., send email, publish, webhook)
    L5_CRITICAL_FINANCIAL_LEGAL = "L5" # Critical financial, legal contract signing, or destructive


@dataclass(frozen=True)
class CapabilityDefinition:
    name: str
    domain: str
    resource: str
    action: str
    risk_level: RiskLevel
    permission_level: PermissionLevel
    requires_approval: bool
    is_strong_approval: bool = False
    description: str = ""


# Default capabilities catalog
CAPABILITY_CATALOG: Dict[str, CapabilityDefinition] = {
    # Sales Domain
    "sales.crm.read": CapabilityDefinition(
        name="sales.crm.read",
        domain="sales",
        resource="crm",
        action="read",
        risk_level=RiskLevel.L1_INTERNAL_READ,
        permission_level=PermissionLevel.L0_READ,
        requires_approval=False,
        description="Read CRM pipeline data and leads",
    ),
    "sales.crm.write": CapabilityDefinition(
        name="sales.crm.write",
        domain="sales",
        resource="crm",
        action="write",
        risk_level=RiskLevel.L2_DRAFT_WRITE,
        permission_level=PermissionLevel.L2_DRAFT,
        requires_approval=False,
        description="Update CRM lead status and contact records",
    ),
    "sales.pipeline.read": CapabilityDefinition(
        name="sales.pipeline.read",
        domain="sales",
        resource="pipeline",
        action="read",
        risk_level=RiskLevel.L1_INTERNAL_READ,
        permission_level=PermissionLevel.L0_READ,
        requires_approval=False,
        description="Read sales pipeline snapshot and leads",
    ),
    "sales.lead.enrich": CapabilityDefinition(
        name="sales.lead.enrich",
        domain="sales",
        resource="lead",
        action="enrich",
        risk_level=RiskLevel.L1_INTERNAL_READ,
        permission_level=PermissionLevel.L0_READ,
        requires_approval=False,
        description="Enrich lead with research information",
    ),
    "sales.outreach.draft": CapabilityDefinition(
        name="sales.outreach.draft",
        domain="sales",
        resource="outreach",
        action="draft",
        risk_level=RiskLevel.L2_DRAFT_WRITE,
        permission_level=PermissionLevel.L2_DRAFT,
        requires_approval=False,
        description="Draft sales outreach communication",
    ),
    "sales.outreach.send": CapabilityDefinition(
        name="sales.outreach.send",
        domain="sales",
        resource="outreach",
        action="send",
        risk_level=RiskLevel.L4_EXTERNAL_SIDE_EFFECT,
        permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        requires_approval=True,
        description="Send outreach message or email to external leads",
    ),

    # Email & Communication
    "email.read": CapabilityDefinition(
        name="email.read",
        domain="communication",
        resource="email",
        action="read",
        risk_level=RiskLevel.L1_INTERNAL_READ,
        permission_level=PermissionLevel.L0_READ,
        requires_approval=False,
        description="Read emails from mailbox",
    ),
    "email.draft": CapabilityDefinition(
        name="email.draft",
        domain="communication",
        resource="email",
        action="draft",
        risk_level=RiskLevel.L2_DRAFT_WRITE,
        permission_level=PermissionLevel.L2_DRAFT,
        requires_approval=False,
        description="Create email draft",
    ),
    "email.send": CapabilityDefinition(
        name="email.send",
        domain="communication",
        resource="email",
        action="send",
        risk_level=RiskLevel.L4_EXTERNAL_SIDE_EFFECT,
        permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        requires_approval=True,
        description="Send outgoing email",
    ),

    # Marketing Domain
    "marketing.campaign.read": CapabilityDefinition(
        name="marketing.campaign.read",
        domain="marketing",
        resource="campaign",
        action="read",
        risk_level=RiskLevel.L1_INTERNAL_READ,
        permission_level=PermissionLevel.L0_READ,
        requires_approval=False,
        description="Read marketing campaign data and metrics",
    ),
    "marketing.campaign.create": CapabilityDefinition(
        name="marketing.campaign.create",
        domain="marketing",
        resource="campaign",
        action="create",
        risk_level=RiskLevel.L2_DRAFT_WRITE,
        permission_level=PermissionLevel.L2_DRAFT,
        requires_approval=False,
        description="Draft new marketing campaign",
    ),
    "marketing.campaign.publish": CapabilityDefinition(
        name="marketing.campaign.publish",
        domain="marketing",
        resource="campaign",
        action="publish",
        risk_level=RiskLevel.L4_EXTERNAL_SIDE_EFFECT,
        permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        requires_approval=True,
        description="Publish marketing campaign to live channels",
    ),
    "marketing.post.publish": CapabilityDefinition(
        name="marketing.post.publish",
        domain="marketing",
        resource="post",
        action="publish",
        risk_level=RiskLevel.L4_EXTERNAL_SIDE_EFFECT,
        permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        requires_approval=True,
        description="Publish social media post",
    ),

    # Finance Domain
    "finance.summary.read": CapabilityDefinition(
        name="finance.summary.read",
        domain="finance",
        resource="summary",
        action="read",
        risk_level=RiskLevel.L1_INTERNAL_READ,
        permission_level=PermissionLevel.L0_READ,
        requires_approval=False,
        description="Read financial snapshot and runway summary",
    ),
    "finance.position.read": CapabilityDefinition(
        name="finance.position.read",
        domain="finance",
        resource="position",
        action="read",
        risk_level=RiskLevel.L1_INTERNAL_READ,
        permission_level=PermissionLevel.L0_READ,
        requires_approval=False,
        description="Read financial position and cash runway",
    ),
    "finance.report.generate": CapabilityDefinition(
        name="finance.report.generate",
        domain="finance",
        resource="report",
        action="generate",
        risk_level=RiskLevel.L2_DRAFT_WRITE,
        permission_level=PermissionLevel.L2_DRAFT,
        requires_approval=False,
        description="Generate draft financial management report",
    ),
    "finance.report.create": CapabilityDefinition(
        name="finance.report.create",
        domain="finance",
        resource="report",
        action="create",
        risk_level=RiskLevel.L2_DRAFT_WRITE,
        permission_level=PermissionLevel.L2_DRAFT,
        requires_approval=False,
        description="Create financial optimization report",
    ),
    "finance.approval.request": CapabilityDefinition(
        name="finance.approval.request",
        domain="finance",
        resource="approval",
        action="request",
        risk_level=RiskLevel.L4_EXTERNAL_SIDE_EFFECT,
        permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        requires_approval=True,
        description="Request founder sign-off for financial adjustments",
    ),
    "finance.invoice.issue": CapabilityDefinition(
        name="finance.invoice.issue",
        domain="finance",
        resource="invoice",
        action="issue",
        risk_level=RiskLevel.L4_EXTERNAL_SIDE_EFFECT,
        permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        requires_approval=True,
        description="Issue formal invoice to customer",
    ),
    "finance.payment.transfer": CapabilityDefinition(
        name="finance.payment.transfer",
        domain="finance",
        resource="payment",
        action="transfer",
        risk_level=RiskLevel.L5_CRITICAL_FINANCIAL_LEGAL,
        permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        requires_approval=True,
        is_strong_approval=True,
        description="Initiate or authorize monetary fund transfer",
    ),
    "finance.account.update": CapabilityDefinition(
        name="finance.account.update",
        domain="finance",
        resource="account",
        action="update",
        risk_level=RiskLevel.L5_CRITICAL_FINANCIAL_LEGAL,
        permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        requires_approval=True,
        is_strong_approval=True,
        description="Modify bank account or payment provider settings",
    ),

    # Legal Domain
    "legal.contract.read": CapabilityDefinition(
        name="legal.contract.read",
        domain="legal",
        resource="contract",
        action="read",
        risk_level=RiskLevel.L1_INTERNAL_READ,
        permission_level=PermissionLevel.L0_READ,
        requires_approval=False,
        description="Read legal contract documents",
    ),
    "legal.contract.draft": CapabilityDefinition(
        name="legal.contract.draft",
        domain="legal",
        resource="contract",
        action="draft",
        risk_level=RiskLevel.L2_DRAFT_WRITE,
        permission_level=PermissionLevel.L2_DRAFT,
        requires_approval=False,
        description="Draft legal contract or clause",
    ),
    "legal.contract.sign": CapabilityDefinition(
        name="legal.contract.sign",
        domain="legal",
        resource="contract",
        action="sign",
        risk_level=RiskLevel.L5_CRITICAL_FINANCIAL_LEGAL,
        permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        requires_approval=True,
        is_strong_approval=True,
        description="Execute digital signature on legally binding agreement",
    ),
    "legal.compliance.audit": CapabilityDefinition(
        name="legal.compliance.audit",
        domain="legal",
        resource="compliance",
        action="audit",
        risk_level=RiskLevel.L1_INTERNAL_READ,
        permission_level=PermissionLevel.L0_READ,
        requires_approval=False,
        description="Run compliance and regulatory checklist audit",
    ),

    # Code / Sandbox Execution
    "code.execute": CapabilityDefinition(
        name="code.execute",
        domain="code",
        resource="sandbox",
        action="execute",
        risk_level=RiskLevel.L3_OPERATIONAL_WRITE,
        permission_level=PermissionLevel.L3_EXECUTE,
        requires_approval=False,
        description="Run isolated Python or shell code in OpenSandbox",
    ),
    "code.sandbox.create": CapabilityDefinition(
        name="code.sandbox.create",
        domain="code",
        resource="sandbox",
        action="create",
        risk_level=RiskLevel.L3_OPERATIONAL_WRITE,
        permission_level=PermissionLevel.L2_DRAFT,
        requires_approval=False,
        description="Create and provision a new sandbox environment",
    ),

    # Automations & n8n
    "automation.n8n.read": CapabilityDefinition(
        name="automation.n8n.read",
        domain="automation",
        resource="n8n",
        action="read",
        risk_level=RiskLevel.L1_INTERNAL_READ,
        permission_level=PermissionLevel.L0_READ,
        requires_approval=False,
        description="Inspect n8n workflows and execution status",
    ),
    "automation.n8n.trigger": CapabilityDefinition(
        name="automation.n8n.trigger",
        domain="automation",
        resource="n8n",
        action="trigger",
        risk_level=RiskLevel.L4_EXTERNAL_SIDE_EFFECT,
        permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        requires_approval=True,
        description="Trigger n8n webhook or external workflow execution",
    ),
    "n8n.sales.outreach_dispatch": CapabilityDefinition(
        name="n8n.sales.outreach_dispatch",
        domain="sales",
        resource="n8n",
        action="outreach_dispatch",
        risk_level=RiskLevel.L4_EXTERNAL_SIDE_EFFECT,
        permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        requires_approval=True,
        description="Dispatch outbound sales email/Zalo campaign via n8n",
    ),
    "n8n.finance.alert_dispatch": CapabilityDefinition(
        name="n8n.finance.alert_dispatch",
        domain="finance",
        resource="n8n",
        action="alert_dispatch",
        risk_level=RiskLevel.L4_EXTERNAL_SIDE_EFFECT,
        permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        requires_approval=True,
        description="Dispatch financial alert via n8n webhook",
    ),
    "n8n.marketing.campaign_dispatch": CapabilityDefinition(
        name="n8n.marketing.campaign_dispatch",
        domain="marketing",
        resource="n8n",
        action="campaign_dispatch",
        risk_level=RiskLevel.L4_EXTERNAL_SIDE_EFFECT,
        permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        requires_approval=True,
        description="Dispatch marketing campaign via n8n",
    ),
    "n8n.legal.contract_dispatch": CapabilityDefinition(
        name="n8n.legal.contract_dispatch",
        domain="legal",
        resource="n8n",
        action="contract_dispatch",
        risk_level=RiskLevel.L4_EXTERNAL_SIDE_EFFECT,
        permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        requires_approval=True,
        description="Dispatch legal contract workflow via n8n",
    ),

    # System & Workspace
    "system.workspace.read": CapabilityDefinition(
        name="system.workspace.read",
        domain="system",
        resource="workspace",
        action="read",
        risk_level=RiskLevel.L1_INTERNAL_READ,
        permission_level=PermissionLevel.L0_READ,
        requires_approval=False,
        description="Read workspace configuration and metadata",
    ),
    "system.workspace.update": CapabilityDefinition(
        name="system.workspace.update",
        domain="system",
        resource="workspace",
        action="update",
        risk_level=RiskLevel.L5_CRITICAL_FINANCIAL_LEGAL,
        permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        requires_approval=True,
        is_strong_approval=True,
        description="Modify critical workspace settings or security policies",
    ),

    # OKR & Tasks
    "okr.read": CapabilityDefinition(
        name="okr.read",
        domain="strategy",
        resource="okr",
        action="read",
        risk_level=RiskLevel.L1_INTERNAL_READ,
        permission_level=PermissionLevel.L0_READ,
        requires_approval=False,
        description="Read OKR objectives and key results",
    ),
    "okr.write": CapabilityDefinition(
        name="okr.write",
        domain="strategy",
        resource="okr",
        action="write",
        risk_level=RiskLevel.L3_OPERATIONAL_WRITE,
        permission_level=PermissionLevel.L2_DRAFT,
        requires_approval=False,
        description="Create or update OKR objectives and key results",
    ),
    "project.task.read": CapabilityDefinition(
        name="project.task.read",
        domain="project",
        resource="task",
        action="read",
        risk_level=RiskLevel.L1_INTERNAL_READ,
        permission_level=PermissionLevel.L0_READ,
        requires_approval=False,
        description="Read project tasks and milestones",
    ),
    "project.task.write": CapabilityDefinition(
        name="project.task.write",
        domain="project",
        resource="task",
        action="write",
        risk_level=RiskLevel.L3_OPERATIONAL_WRITE,
        permission_level=PermissionLevel.L2_DRAFT,
        requires_approval=False,
        description="Create or update project tasks and deliverables",
    ),

    # Learning Domain
    "learning.content.read": CapabilityDefinition(
        name="learning.content.read",
        domain="learning",
        resource="content",
        action="read",
        risk_level=RiskLevel.L0_PUBLIC_READ,
        permission_level=PermissionLevel.L0_READ,
        requires_approval=False,
        description="Read learning and curriculum materials",
    ),
    "learning.content.generate": CapabilityDefinition(
        name="learning.content.generate",
        domain="learning",
        resource="content",
        action="generate",
        risk_level=RiskLevel.L2_DRAFT_WRITE,
        permission_level=PermissionLevel.L2_DRAFT,
        requires_approval=False,
        description="Generate learning summaries and quiz questions",
    ),
}


_STANDARD_DOMAINS = {"sales", "finance", "marketing", "legal", "learning", "strategy", "project", "code", "system", "automation"}


def get_capability_definition(capability_name: str) -> Optional[CapabilityDefinition]:
    """Retrieve capability definition by exact name or dynamically derive standard primitive."""
    if capability_name in CAPABILITY_CATALOG:
        return CAPABILITY_CATALOG[capability_name]

    # Dynamically derive standard domain primitives: e.g. "sales.research", "finance.reasoning", etc.
    parts = capability_name.split(".")
    if len(parts) == 2 and parts[0] in _STANDARD_DOMAINS:
        domain, primitive = parts[0], parts[1]
        if primitive in ("research", "data", "read"):
            return CapabilityDefinition(
                name=capability_name,
                domain=domain,
                resource=primitive,
                action="read",
                risk_level=RiskLevel.L1_INTERNAL_READ,
                permission_level=PermissionLevel.L0_READ,
                requires_approval=False,
                description=f"Read {primitive} for domain {domain}",
            )
        if primitive in ("reasoning", "evaluate", "evaluation"):
            return CapabilityDefinition(
                name=capability_name,
                domain=domain,
                resource=primitive,
                action="evaluate",
                risk_level=RiskLevel.L1_INTERNAL_READ,
                permission_level=PermissionLevel.L1_SUGGEST,
                requires_approval=False,
                description=f"Perform {primitive} reasoning for domain {domain}",
            )
        if primitive in ("communication", "draft", "write"):
            return CapabilityDefinition(
                name=capability_name,
                domain=domain,
                resource=primitive,
                action="draft",
                risk_level=RiskLevel.L2_DRAFT_WRITE,
                permission_level=PermissionLevel.L2_DRAFT,
                requires_approval=False,
                description=f"Draft {primitive} for domain {domain}",
            )
        if primitive in ("action", "execute", "dispatch"):
            return CapabilityDefinition(
                name=capability_name,
                domain=domain,
                resource=primitive,
                action="execute",
                risk_level=RiskLevel.L4_EXTERNAL_SIDE_EFFECT,
                permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
                requires_approval=True,
                description=f"Execute {primitive} action for domain {domain}",
            )

    if capability_name.startswith("n8n.") or capability_name.endswith(".dispatch"):
        return CapabilityDefinition(
            name=capability_name,
            domain=parts[0] if parts else "automation",
            resource="n8n",
            action=capability_name,
            risk_level=RiskLevel.L4_EXTERNAL_SIDE_EFFECT,
            permission_level=PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
            requires_approval=True,
            description=f"Execute workflow or dispatch action {capability_name}",
        )

    if capability_name.startswith("web.") or capability_name.endswith(".search"):
        return CapabilityDefinition(
            name=capability_name,
            domain="web",
            resource="search",
            action="search",
            risk_level=RiskLevel.L0_PUBLIC_READ,
            permission_level=PermissionLevel.L0_READ,
            requires_approval=False,
            description=f"Public web query {capability_name}",
        )

    if capability_name.endswith(".read"):
        domain = parts[0] if parts else "system"
        return CapabilityDefinition(
            name=capability_name,
            domain=domain,
            resource=parts[1] if len(parts) > 1 else "data",
            action="read",
            risk_level=RiskLevel.L1_INTERNAL_READ,
            permission_level=PermissionLevel.L0_READ,
            requires_approval=False,
            description=f"Read internal data for {capability_name}",
        )

    if capability_name.endswith(".draft") or capability_name.endswith(".review_draft") or capability_name.endswith(".create") or capability_name.endswith(".generate"):
        domain = parts[0] if parts else "system"
        return CapabilityDefinition(
            name=capability_name,
            domain=domain,
            resource=parts[1] if len(parts) > 1 else "draft",
            action="draft",
            risk_level=RiskLevel.L2_DRAFT_WRITE,
            permission_level=PermissionLevel.L2_DRAFT,
            requires_approval=False,
            description=f"Draft document or data for {capability_name}",
        )

    if capability_name.endswith(".audit") or capability_name.endswith(".check"):
        domain = parts[0] if parts else "system"
        return CapabilityDefinition(
            name=capability_name,
            domain=domain,
            resource=parts[1] if len(parts) > 1 else "audit",
            action="audit",
            risk_level=RiskLevel.L1_INTERNAL_READ,
            permission_level=PermissionLevel.L0_READ,
            requires_approval=False,
            description=f"Perform internal audit or check {capability_name}",
        )

    return None


def list_capabilities(domain: Optional[str] = None) -> List[CapabilityDefinition]:
    """List all registered capabilities, optionally filtered by domain."""
    if domain:
        return [c for c in CAPABILITY_CATALOG.values() if c.domain == domain]
    return list(CAPABILITY_CATALOG.values())
