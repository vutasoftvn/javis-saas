"""
COSA Workflows Definitions Package
"""
from workflows.definitions.financial_health import (
    get_financial_health_workflow,
    get_staging_deployment_workflow,
)
from workflows.definitions.lead_outreach import get_lead_outreach_workflow
from workflows.definitions.market_analysis import get_market_analysis_workflow

__all__ = [
    "get_financial_health_workflow",
    "get_lead_outreach_workflow",
    "get_market_analysis_workflow",
    "get_staging_deployment_workflow",
]
