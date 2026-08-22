"""Data-driven agent presets defining permissions, tools, and roles."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AgentPreset:
    agent_key: str
    name: str
    description: str
    tool_flat_names: tuple[str, ...]
    write_tools: tuple[str, ...]
    requires_approval: bool
    permission_profile: str


AGENT_PRESETS: dict[str, AgentPreset] = {
    "chief_of_staff": AgentPreset(
        agent_key="chief_of_staff",
        name="Chief of Staff",
        description="Executive orchestrator for high-level diagnosis, cross-domain synthesis, and strategic planning.",
        tool_flat_names=(
            "sales_get_pipeline_summary",
            "sales_get_lead_details",
            "sales_list_active_opportunities",
            "sales_analyze_sales_data",
            "finance_get_financial_summary",
            "finance_get_period_overview",
            "finance_analyze_financial_data",
            "strategy_list_okrs",
            "strategy_list_projects",
            "tasks_list_tasks",
            "execution_run_python",
            "execution_run_browser_research",
        ),
        write_tools=(),
        requires_approval=True,
        permission_profile="chief_of_staff_suggest",
    ),
    "sales_specialist": AgentPreset(
        agent_key="sales_specialist",
        name="Sales Specialist",
        description="Specialist in CRM pipeline analytics, lead tracking, and deal follow-up actions.",
        tool_flat_names=(
            "sales_get_pipeline_summary",
            "sales_get_lead_details",
            "sales_list_active_opportunities",
            "sales_create_activity",
            "sales_analyze_sales_data",
            "execution_run_python",
        ),
        write_tools=(
            "sales_create_activity",
        ),
        requires_approval=False,
        permission_profile="L1_SUGGEST",
    ),
    "finance_specialist": AgentPreset(
        agent_key="finance_specialist",
        name="Finance Specialist",
        description="Specialist in cashflow, runway calculations, P&L reporting, and cost breakdowns.",
        tool_flat_names=(
            "finance_get_financial_summary",
            "finance_get_period_overview",
            "finance_analyze_financial_data",
            "execution_run_python",
        ),
        write_tools=(),
        requires_approval=False,
        permission_profile="L0_READ",
    ),
    "data_analyst": AgentPreset(
        agent_key="data_analyst",
        name="Data Analyst",
        description="Analytics agent running python scripts and data transformations in sandboxed environments.",
        tool_flat_names=(
            "sales_get_pipeline_summary",
            "finance_get_financial_summary",
            "execution_run_python",
            "execution_run_browser_research",
        ),
        write_tools=(
            "execution_run_python",
        ),
        requires_approval=False,
        permission_profile="L2_DRAFT",
    ),
    "researcher": AgentPreset(
        agent_key="researcher",
        name="Researcher",
        description="Market and web research agent executing browser crawls and summarizing findings.",
        tool_flat_names=(
            "execution_run_browser_research",
            "strategy_list_projects",
        ),
        write_tools=(),
        requires_approval=False,
        permission_profile="L0_READ",
    ),
    "coding_agent": AgentPreset(
        agent_key="coding_agent",
        name="Coding Agent",
        description="Autonomous developer agent for git repository modifications and code patching in sandbox.",
        tool_flat_names=(
            "execution_run_coding_task",
            "execution_run_python",
        ),
        write_tools=(
            "execution_run_coding_task",
        ),
        requires_approval=True,
        permission_profile="L2_DRAFT",
    ),
    "google_search": AgentPreset(
        agent_key="google_search",
        name="Google Search Agent",
        description="Dedicated search agent retrieving and summarizing internet research and website information.",
        tool_flat_names=(
            "google.search",
            "web.extract",
            "knowledge.search",
        ),
        write_tools=(),
        requires_approval=False,
        permission_profile="L0_READ",
    ),
}


def get_preset(agent_key: str) -> Optional[AgentPreset]:
    """Retrieve an AgentPreset by its unique agent_key."""
    return AGENT_PRESETS.get(agent_key)


def list_presets() -> list[AgentPreset]:
    """List all registered agent presets."""
    return list(AGENT_PRESETS.values())
