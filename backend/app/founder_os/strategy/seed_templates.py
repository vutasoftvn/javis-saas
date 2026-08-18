"""Versioned system seed templates (design §"Templates, capabilities, and agents").

Each seed is a workspace-local template blueprint: a capability area with the
deliverables, evidence requirements, execution modes and risk level a stage's
AI routing assessment reasons about. Seeds are internal defaults released with
the product; workspaces get an editable local copy via
`TemplateService.provision_workspace_templates`, never a live reference to
this module.
"""

EXECUTION_MODES_FULL = ["MANUAL", "AI_ASSISTED", "AUTONOMOUS"]
EXECUTION_MODES_SUPERVISED = ["MANUAL", "AI_ASSISTED"]

SEED_TEMPLATES = [
    {
        "source_key": "core_startup",
        "name": "Core Startup",
        "capabilities": [
            {
                "capability_key": "core_startup.research_validation",
                "name": "Research & Validation",
                "expected_deliverables": ["Problem interview notes", "Demand validation summary"],
                "evidence_requirements": ["customer_interview", "market_report"],
                "supported_execution_modes": EXECUTION_MODES_FULL,
                "risk_level": "LOW",
                "professional_review_required": False,
            },
            {
                "capability_key": "core_startup.product_planning",
                "name": "Product Planning",
                "expected_deliverables": ["MVP scope draft", "Non-goals list"],
                "evidence_requirements": ["internal_metric", "note"],
                "supported_execution_modes": EXECUTION_MODES_FULL,
                "risk_level": "LOW",
                "professional_review_required": False,
            },
            {
                "capability_key": "core_startup.execution_coordination",
                "name": "Execution Coordination",
                "expected_deliverables": ["Weekly commitment plan", "Blocker log"],
                "evidence_requirements": ["internal_metric"],
                "supported_execution_modes": EXECUTION_MODES_FULL,
                "risk_level": "LOW",
                "professional_review_required": False,
            },
            {
                "capability_key": "core_startup.kpi_evidence_analysis",
                "name": "KPI & Evidence Analysis",
                "expected_deliverables": ["Metric check-in summary", "Evidence gap report"],
                "evidence_requirements": ["internal_metric"],
                "supported_execution_modes": EXECUTION_MODES_FULL,
                "risk_level": "LOW",
                "professional_review_required": False,
            },
        ],
    },
    {
        "source_key": "technology_security",
        "name": "Technology and Security",
        "capabilities": [
            {
                "capability_key": "technology_security.architecture_review",
                "name": "Architecture Review",
                "expected_deliverables": ["Architecture decision record"],
                "evidence_requirements": ["internal_metric"],
                "supported_execution_modes": EXECUTION_MODES_FULL,
                "risk_level": "MEDIUM",
                "professional_review_required": False,
            },
            {
                "capability_key": "technology_security.security_review",
                "name": "Security Review",
                "expected_deliverables": ["Security risk checklist"],
                "evidence_requirements": ["internal_metric", "regulation"],
                "supported_execution_modes": EXECUTION_MODES_SUPERVISED,
                "risk_level": "HIGH",
                "professional_review_required": False,
            },
        ],
    },
    {
        "source_key": "finance_unit_economics",
        "name": "Finance and Unit Economics",
        "capabilities": [
            {
                "capability_key": "finance_unit_economics.unit_economics_model",
                "name": "Unit Economics Model",
                "expected_deliverables": ["Unit economics forecast narrative"],
                "evidence_requirements": ["internal_metric", "market_report"],
                "supported_execution_modes": EXECUTION_MODES_SUPERVISED,
                "risk_level": "MEDIUM",
                "professional_review_required": False,
            },
            {
                "capability_key": "finance_unit_economics.budget_planning",
                "name": "Budget Planning",
                "expected_deliverables": ["Stage budget plan"],
                "evidence_requirements": ["internal_metric"],
                "supported_execution_modes": EXECUTION_MODES_SUPERVISED,
                "risk_level": "MEDIUM",
                "professional_review_required": False,
            },
        ],
    },
    {
        "source_key": "legal_compliance",
        "name": "Legal and Compliance",
        "capabilities": [
            {
                "capability_key": "legal_compliance.compliance_checklist",
                "name": "Compliance Checklist",
                "expected_deliverables": ["Compliance checklist draft"],
                "evidence_requirements": ["regulation"],
                "supported_execution_modes": EXECUTION_MODES_SUPERVISED,
                "risk_level": "REGULATED",
                "professional_review_required": True,
            },
        ],
    },
    {
        "source_key": "growth_gtm",
        "name": "Growth and Go-to-market",
        "capabilities": [
            {
                "capability_key": "growth_gtm.channel_strategy",
                "name": "Channel Strategy",
                "expected_deliverables": ["Channel prioritization brief"],
                "evidence_requirements": ["market_report", "competitor"],
                "supported_execution_modes": EXECUTION_MODES_FULL,
                "risk_level": "LOW",
                "professional_review_required": False,
            },
            {
                "capability_key": "growth_gtm.campaign_planning",
                "name": "Campaign Planning",
                "expected_deliverables": ["Launch campaign plan"],
                "evidence_requirements": ["internal_metric"],
                "supported_execution_modes": EXECUTION_MODES_FULL,
                "risk_level": "LOW",
                "professional_review_required": False,
            },
        ],
    },
    {
        "source_key": "operations",
        "name": "Operations",
        "capabilities": [
            {
                "capability_key": "operations.process_setup",
                "name": "Process Setup",
                "expected_deliverables": ["Operating process checklist"],
                "evidence_requirements": ["internal_metric", "note"],
                "supported_execution_modes": EXECUTION_MODES_FULL,
                "risk_level": "LOW",
                "professional_review_required": False,
            },
        ],
    },
]

SEED_TEMPLATES_BY_KEY = {seed["source_key"]: seed for seed in SEED_TEMPLATES}
