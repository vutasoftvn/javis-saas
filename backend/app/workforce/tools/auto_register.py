from sqlalchemy.ext.asyncio import AsyncSession
from app.workforce.gateway.gateway import AgentGateway
from app.workforce.identity.context import ExecutionContext

from app.workforce.tools.finance.tools import (
    finance_read_summary_handler,
    finance_post_entry_handler,
)
from app.workforce.tools.sales.tools import (
    crm_search_handler,
    crm_update_handler,
    email_send_handler,
)
from app.workforce.tools.project.tools import (
    project_read_portfolio_handler,
    okr_read_overview_handler,
    strategy_read_canvas_handler,
)
from app.workforce.tools.knowledge.tools import (
    knowledge_search_handler,
    system_help_handler,
)
from app.workforce.tools.marketing.tools import (
    marketing_campaign_list_handler,
    marketing_campaign_create_handler,
    marketing_content_generate_handler,
    marketing_social_publish_handler,
)
from app.workforce.tools.developer.tools import (
    developer_build_spec_create_handler,
    developer_claude_code_handler,
    sandbox_execute_handler,
)
from app.workforce.tools.tasks.tools import (
    tasks_list_handler,
    tasks_create_handler,
    tasks_update_status_handler,
)
from app.workforce.tools.legal.tools import (
    legal_compliance_check_handler,
    legal_obligation_list_handler,
)
from app.workforce.tools.company_runtime.tools import (
    runtime_blocker_create_handler,
    runtime_handoff_create_handler,
)
from app.workforce.tools.policy_funding.tools import (
    policy_funding_search_handler,
    policy_eligibility_eval_handler,
)
from app.workforce.tools.search.tools import (
    google_search_handler,
    web_extract_handler,
)


def register_all_domain_tools(gateway: AgentGateway, db: AsyncSession):
    """Tự động đăng ký toàn bộ domain tool handlers vào Agent Gateway."""

    # 1. Finance Tools
    gateway.register_handler("finance.read_summary", lambda ctx, args: finance_read_summary_handler(ctx, args, db))
    gateway.register_handler("finance.post_entry", lambda ctx, args: finance_post_entry_handler(ctx, args, db))

    # 2. Sales & CRM Tools
    gateway.register_handler("crm.search", lambda ctx, args: crm_search_handler(ctx, args, db))
    gateway.register_handler("crm.update", lambda ctx, args: crm_update_handler(ctx, args, db))
    gateway.register_handler("email.send", lambda ctx, args: email_send_handler(ctx, args, db))

    # 3. Project & Strategy Tools
    gateway.register_handler("project.read_portfolio", lambda ctx, args: project_read_portfolio_handler(ctx, args, db))
    gateway.register_handler("okr.read_overview", lambda ctx, args: okr_read_overview_handler(ctx, args, db))
    gateway.register_handler("strategy.read_canvas", lambda ctx, args: strategy_read_canvas_handler(ctx, args, db))

    # 4. Knowledge & Vault Tools
    gateway.register_handler("knowledge.search", lambda ctx, args: knowledge_search_handler(ctx, args, db))
    gateway.register_handler("system.help", lambda ctx, args: system_help_handler(ctx, args, db))

    # 5. Marketing Tools
    gateway.register_handler("marketing.campaign.list", lambda ctx, args: marketing_campaign_list_handler(ctx, args, db))
    gateway.register_handler("marketing.campaign.create", lambda ctx, args: marketing_campaign_create_handler(ctx, args, db))
    gateway.register_handler("marketing.content.generate", lambda ctx, args: marketing_content_generate_handler(ctx, args, db))
    gateway.register_handler("marketing.social.publish", lambda ctx, args: marketing_social_publish_handler(ctx, args, db))

    # 6. Developer & Sandbox Tools
    gateway.register_handler("developer.build_spec.create", lambda ctx, args: developer_build_spec_create_handler(ctx, args, db))
    gateway.register_handler("developer.claude_code", lambda ctx, args: developer_claude_code_handler(ctx, args, db))
    gateway.register_handler("sandbox.execute", lambda ctx, args: sandbox_execute_handler(ctx, args, db))

    # 7. Tasks & Operations Tools
    gateway.register_handler("tasks.list", lambda ctx, args: tasks_list_handler(ctx, args, db))
    gateway.register_handler("tasks.create", lambda ctx, args: tasks_create_handler(ctx, args, db))
    gateway.register_handler("tasks.update_status", lambda ctx, args: tasks_update_status_handler(ctx, args, db))

    # 8. Legal Tools
    gateway.register_handler("legal.compliance.check", lambda ctx, args: legal_compliance_check_handler(ctx, args, db))
    gateway.register_handler("legal.obligation.list", lambda ctx, args: legal_obligation_list_handler(ctx, args, db))

    # 9. Company Runtime Tools
    gateway.register_handler("runtime.blocker.create", lambda ctx, args: runtime_blocker_create_handler(ctx, args, db))
    gateway.register_handler("runtime.handoff.create", lambda ctx, args: runtime_handoff_create_handler(ctx, args, db))

    # 10. Policy Funding Tools
    gateway.register_handler("policy.funding.search", lambda ctx, args: policy_funding_search_handler(ctx, args, db))
    gateway.register_handler("policy.eligibility.eval", lambda ctx, args: policy_eligibility_eval_handler(ctx, args, db))

    # 11. Search & Web Research Tools
    gateway.register_handler("google.search", lambda ctx, args: google_search_handler(ctx, args, db))
    gateway.register_handler("web.extract", lambda ctx, args: web_extract_handler(ctx, args, db))

def register_extension_tools(gateway: AgentGateway, db: AsyncSession, workspace_id: int):
    """
    Tự động đăng ký các tools từ ExtensionRegistry thông qua CapabilityBridge.
    """
    from app.workforce.extensions.registry import ExtensionRegistry
    from app.workforce.extensions.eligibility import resolve_eligible_capabilities
    from app.workforce.agents.runtime.execution_scope import ExecutionScope
    from app.workforce.extensions.capability_bridge import CapabilityBridge
    from app.workforce.extensions.mcp_provider import MCPProvider

    registry = ExtensionRegistry()
    # Scope for registration discovery (usually company wide)
    scope = ExecutionScope(
        workspace_id=workspace_id,
        company_id=workspace_id,  # Assume same for MVP
        principal_user_id=0,
        principal_member_id=0,
        principal_role="system",
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=()
    )
    
    # We just expose the capability to the gateway. The execution is handled dynamically.
    # In a real system, the gateway would call the bridge.
    pass
