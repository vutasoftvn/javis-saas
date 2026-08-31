from __future__ import annotations

from typing import Any

from agent.artifacts import ArtifactRepository
from agent.capabilities.registry import CapabilityRegistry
from agent.capabilities.web_search import (
    WebSearchBudgetStore,
    WebSearchProvider,
    build_web_search_provider,
)

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.commercial_customer_read import (
    COMMERCIAL_CUSTOMER_360_READ_SPEC,
    create_commercial_customer_360_read_handler,
)
from apps.cosa.capabilities.engagement_assignment_write import (
    ENGAGEMENT_ASSIGNMENT_WRITE_SPEC,
    create_engagement_assignment_write_handler,
)
from apps.cosa.capabilities.engagement_message_draft import (
    ENGAGEMENT_MESSAGE_DRAFT_SPEC,
    create_engagement_message_draft_handler,
)
from apps.cosa.capabilities.engagement_message_send import (
    ENGAGEMENT_MESSAGE_SEND_SPEC,
    create_engagement_message_send_handler,
)
from apps.cosa.capabilities.engagement_read import (
    ENGAGEMENT_THREAD_READ_SPEC,
    create_engagement_thread_read_handler,
)
from apps.cosa.capabilities.finance_read import (
    FINANCE_CONNECTION_READ_SPEC,
    FINANCE_TRANSACTION_READ_SPEC,
    create_finance_connection_read_handler,
    create_finance_transaction_read_handler,
)
from apps.cosa.capabilities.finance_write import (
    FINANCE_ACCOUNTING_DOCUMENT_CONFIRM_SPEC,
    FINANCE_ACCOUNTING_DOCUMENT_CREATE_DRAFT_SPEC,
    FINANCE_TRANSACTION_CLASSIFY_PROPOSE_SPEC,
    FINANCE_TRANSACTION_RECORD_SPEC,
    create_finance_accounting_document_confirm_handler,
    create_finance_accounting_document_create_draft_handler,
    create_finance_transaction_classify_propose_handler,
    create_finance_transaction_record_handler,
)
from apps.cosa.capabilities.knowledge_read import (
    KNOWLEDGE_PROFILE_READ_SPEC,
    create_knowledge_profile_read_handler,
)
from apps.cosa.capabilities.legal_read import (
    LEGAL_APPLICABILITY_ASSESS_SPEC,
    create_legal_applicability_assess_handler,
)
from apps.cosa.capabilities.legal_write import (
    LEGAL_OBLIGATION_CREATE_DRAFT_SPEC,
    create_legal_obligation_create_draft_handler,
)
from apps.cosa.capabilities.marketing_read import (
    MARKETING_CONTEXT_READ_SPEC,
    create_marketing_context_read_handler,
)
from apps.cosa.capabilities.marketing_write import (
    CAMPAIGN_ASSET_WRITE_SPEC,
    EXPERIMENT_WRITE_SPEC,
    MARKETING_CONTEXT_WRITE_SPEC,
    create_campaign_asset_write_handler,
    create_experiment_write_handler,
    create_marketing_context_write_handler,
)
from apps.cosa.capabilities.operations_read import (
    OPERATIONS_TASK_LIST_SPEC,
    OPERATIONS_TASK_READ_SPEC,
    create_operations_task_list_handler,
    create_operations_task_read_handler,
)
from apps.cosa.capabilities.operations_write import (
    OPERATIONS_TASK_CREATE_DRAFT_SPEC,
    create_operations_task_create_draft_handler,
)
from apps.cosa.capabilities.project_lifecycle import (
    ANALYTICS_METRIC_CONTRACT_GET_SPEC,
    ANALYTICS_PMF_SCOREBOARD_GET_SPEC,
    ANALYTICS_PMF_SCOREBOARD_PROPOSE_SPEC,
    STRATEGY_EVIDENCE_CREATE_SPEC,
    STRATEGY_EVIDENCE_LIST_SPEC,
    STRATEGY_GATE_EVALUATION_CREATE_SPEC,
    STRATEGY_NEXT_BEST_ACTION_GET_SPEC,
    STRATEGY_PILOT_CREATE_DRAFT_SPEC,
    STRATEGY_PILOT_GET_SPEC,
    STRATEGY_PROJECT_GET_SPEC,
    create_analytics_metric_contract_get_handler,
    create_analytics_pmf_scoreboard_get_handler,
    create_analytics_pmf_scoreboard_propose_handler,
    create_strategy_evidence_create_handler,
    create_strategy_evidence_list_handler,
    create_strategy_gate_evaluation_create_handler,
    create_strategy_next_best_action_get_handler,
    create_strategy_pilot_create_draft_handler,
    create_strategy_pilot_get_handler,
    create_strategy_project_get_handler,
)
from apps.cosa.capabilities.sandbox_read_mcp import register_sandbox_read_mcp_tools
from apps.cosa.capabilities.venture_profile import (
    VENTURE_PROFILE_PROPOSE_UPDATE_SPEC,
    VENTURE_PROFILE_READ_SPEC,
    create_venture_profile_propose_update_handler,
    create_venture_profile_read_handler,
)
from apps.cosa.capabilities.venture_stage import (
    VENTURE_STAGE_ASSESS_SPEC,
    create_venture_stage_assess_handler,
)
from apps.cosa.capabilities.web_search import (
    WEB_SEARCH_SPEC,
    create_web_search_handler,
)
from apps.cosa.policies.company_policy_client import CosaTenantPolicyClient


def register_cosa_capabilities(
    cap_registry: CapabilityRegistry,
    *,
    client: CompanyServiceClient,
    tenant_policy: CosaTenantPolicyClient,
    search_budget: WebSearchBudgetStore,
    artifact_repo: ArtifactRepository,
    web_search_provider: WebSearchProvider | None = None,
) -> None:
    """Đăng ký toàn bộ capability specs và handlers cho CosaAgentPlane."""
    # Operations
    cap_registry.register(OPERATIONS_TASK_LIST_SPEC, create_operations_task_list_handler(client))
    cap_registry.register(OPERATIONS_TASK_READ_SPEC, create_operations_task_read_handler(client))
    cap_registry.register(
        OPERATIONS_TASK_CREATE_DRAFT_SPEC,
        create_operations_task_create_draft_handler(client),
    )

    # Finance
    cap_registry.register(
        FINANCE_TRANSACTION_RECORD_SPEC, create_finance_transaction_record_handler(client)
    )
    cap_registry.register(
        FINANCE_CONNECTION_READ_SPEC, create_finance_connection_read_handler(client)
    )
    cap_registry.register(
        FINANCE_TRANSACTION_READ_SPEC, create_finance_transaction_read_handler(client)
    )
    cap_registry.register(
        FINANCE_TRANSACTION_CLASSIFY_PROPOSE_SPEC,
        create_finance_transaction_classify_propose_handler(client),
    )
    cap_registry.register(
        FINANCE_ACCOUNTING_DOCUMENT_CREATE_DRAFT_SPEC,
        create_finance_accounting_document_create_draft_handler(client),
    )
    cap_registry.register(
        FINANCE_ACCOUNTING_DOCUMENT_CONFIRM_SPEC,
        create_finance_accounting_document_confirm_handler(client),
    )

    # Marketing
    cap_registry.register(
        MARKETING_CONTEXT_READ_SPEC, create_marketing_context_read_handler(client)
    )
    cap_registry.register(
        MARKETING_CONTEXT_WRITE_SPEC, create_marketing_context_write_handler(client)
    )
    cap_registry.register(CAMPAIGN_ASSET_WRITE_SPEC, create_campaign_asset_write_handler(client))
    cap_registry.register(EXPERIMENT_WRITE_SPEC, create_experiment_write_handler(client))

    # Engagement & Commercial
    cap_registry.register(
        ENGAGEMENT_THREAD_READ_SPEC, create_engagement_thread_read_handler(client)
    )
    cap_registry.register(
        COMMERCIAL_CUSTOMER_360_READ_SPEC, create_commercial_customer_360_read_handler(client)
    )
    cap_registry.register(ENGAGEMENT_MESSAGE_DRAFT_SPEC, create_engagement_message_draft_handler())
    cap_registry.register(
        ENGAGEMENT_MESSAGE_SEND_SPEC, create_engagement_message_send_handler(client)
    )
    cap_registry.register(
        ENGAGEMENT_ASSIGNMENT_WRITE_SPEC, create_engagement_assignment_write_handler(client)
    )

    # Knowledge & Legal
    cap_registry.register(KNOWLEDGE_PROFILE_READ_SPEC, create_knowledge_profile_read_handler())
    cap_registry.register(
        LEGAL_APPLICABILITY_ASSESS_SPEC, create_legal_applicability_assess_handler(client)
    )
    cap_registry.register(
        LEGAL_OBLIGATION_CREATE_DRAFT_SPEC, create_legal_obligation_create_draft_handler(client)
    )

    # Venture
    cap_registry.register(VENTURE_PROFILE_READ_SPEC, create_venture_profile_read_handler(client))
    cap_registry.register(
        VENTURE_PROFILE_PROPOSE_UPDATE_SPEC, create_venture_profile_propose_update_handler(client)
    )
    cap_registry.register(
        VENTURE_STAGE_ASSESS_SPEC,
        create_venture_stage_assess_handler(client),
    )

    # Strategy
    cap_registry.register(
        STRATEGY_PROJECT_GET_SPEC,
        create_strategy_project_get_handler(client),
    )
    cap_registry.register(
        STRATEGY_EVIDENCE_LIST_SPEC,
        create_strategy_evidence_list_handler(client),
    )
    cap_registry.register(
        STRATEGY_EVIDENCE_CREATE_SPEC,
        create_strategy_evidence_create_handler(client),
    )
    cap_registry.register(
        STRATEGY_GATE_EVALUATION_CREATE_SPEC,
        create_strategy_gate_evaluation_create_handler(client),
    )
    cap_registry.register(
        STRATEGY_NEXT_BEST_ACTION_GET_SPEC,
        create_strategy_next_best_action_get_handler(client),
    )
    cap_registry.register(
        STRATEGY_PILOT_GET_SPEC,
        create_strategy_pilot_get_handler(client),
    )
    cap_registry.register(
        STRATEGY_PILOT_CREATE_DRAFT_SPEC,
        create_strategy_pilot_create_draft_handler(client),
    )

    # Analytics
    cap_registry.register(
        ANALYTICS_METRIC_CONTRACT_GET_SPEC,
        create_analytics_metric_contract_get_handler(client),
    )
    cap_registry.register(
        ANALYTICS_PMF_SCOREBOARD_GET_SPEC,
        create_analytics_pmf_scoreboard_get_handler(client),
    )
    cap_registry.register(
        ANALYTICS_PMF_SCOREBOARD_PROPOSE_SPEC,
        create_analytics_pmf_scoreboard_propose_handler(client),
    )

    # Web Search
    search_prov = web_search_provider or build_web_search_provider()
    cap_registry.register(
        WEB_SEARCH_SPEC,
        create_web_search_handler(
            search_prov,
            workspace_policy_client=tenant_policy,
            budget_store=search_budget,
            artifact_repository=artifact_repo,
        ),
    )

    # Sandbox MCP
    register_sandbox_read_mcp_tools(cap_registry)
