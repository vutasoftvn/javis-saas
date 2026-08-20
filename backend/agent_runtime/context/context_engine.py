"""
COSA Context Engine Implementation
Điều phối nạp ngữ cảnh có chọn lọc, thực thi Explicit Context Rule và quản lý Context Budget (Structure.md Mục 16, 17, 18).
"""
import json
from typing import Any, Dict, List, Optional
from agent.context.base import (
    ContextBudget,
    ContextEngineInterface,
    ContextScope,
    ResolvedContext,
)
from agent.context.resolvers.company_resolver import CompanyScopeResolver
from agent.context.resolvers.knowledge_resolver import KnowledgeScopeResolver
from agent.context.resolvers.project_resolver import ProjectScopeResolver
from agent.context.resolvers.startup_stage_resolver import StartupStageResolver
from agent.routing.base import IntentClassificationResult


class ContextEngine(ContextEngineInterface):
    """Hiện thực bộ máy nạp ngữ cảnh thông minh của COSA"""

    def __init__(self, default_budget: Optional[ContextBudget] = None):
        self.default_budget = default_budget or ContextBudget(max_context_tokens=8000)

    @staticmethod
    def should_load_project(
        intent_result: Optional[IntentClassificationResult] = None,
        session_project_id: Optional[str] = None,
        ui_selected_project_id: Optional[str] = None
    ) -> bool:
        """
        Kiểm tra 4 điều kiện của Explicit Context Rule (Structure.md Mục 16):
        1. User explicitly mentions project in intent.
        2. Session is already scoped to a project.
        3. UI explicitly selected a project.
        """
        if intent_result and intent_result.requires_project_context:
            return True
        if session_project_id:
            return True
        if ui_selected_project_id:
            return True
        return False

    async def resolve_context(
        self, 
        scopes: List[ContextScope], 
        params: Dict[str, Any], 
        budget: Optional[ContextBudget] = None
    ) -> ResolvedContext:
        """Nạp các ngữ cảnh cần thiết và kiểm soát trong phạm vi ngân sách token"""
        active_budget = budget or self.default_budget
        operational_data: Dict[str, Any] = {}
        domain_knowledge = ""
        system_instructions = "Bạn là Co-founder / AI Executive trong hệ điều hành COSA. Hãy tư vấn chính xác, có cấu trúc."
        included_scopes: List[ContextScope] = []

        # 1. Company Scope
        if ContextScope.COMPANY in scopes and params.get("company_id"):
            company_data = await CompanyScopeResolver.resolve(params["company_id"])
            operational_data["company"] = company_data
            included_scopes.append(ContextScope.COMPANY)

        # 2. Project Scope (Tuân thủ Explicit Context Rule)
        if ContextScope.PROJECT in scopes and params.get("project_id"):
            project_data = await ProjectScopeResolver.resolve(params["project_id"])
            operational_data["project"] = project_data
            included_scopes.append(ContextScope.PROJECT)

        # 3. Startup Stage Scope
        if ContextScope.STARTUP_STAGE in scopes:
            stage_name = params.get("startup_stage", "MVP")
            stage_data = await StartupStageResolver.resolve(stage_name)
            operational_data["startup_stage"] = stage_data
            included_scopes.append(ContextScope.STARTUP_STAGE)

        # 4. Knowledge Scope
        if ContextScope.KNOWLEDGE in scopes and params.get("domain"):
            knowledge_data = await KnowledgeScopeResolver.resolve(params["domain"], params.get("query"))
            domain_knowledge = json.dumps(knowledge_data, ensure_ascii=False)
            included_scopes.append(ContextScope.KNOWLEDGE)

        # Tính toán ước tính token (4 ký tự ~ 1 token)
        raw_text_repr = json.dumps(operational_data, ensure_ascii=False) + domain_knowledge + system_instructions
        estimated_tokens = len(raw_text_repr) // 4

        # Nén ngữ cảnh nếu vượt quá ngân sách
        if estimated_tokens > active_budget.max_context_tokens:
            domain_knowledge = self.compress_context(domain_knowledge, active_budget.max_context_tokens // 2)
            estimated_tokens = active_budget.max_context_tokens

        return ResolvedContext(
            scopes=included_scopes,
            system_instructions=system_instructions,
            domain_knowledge=domain_knowledge,
            operational_data=operational_data,
            total_estimated_tokens=estimated_tokens,
            metadata={"budget_applied": active_budget.max_context_tokens}
        )

    def compress_context(self, raw_data: str, max_tokens: int) -> str:
        """Rút gọn và nén dữ liệu văn bản khi vượt quá ngân sách"""
        max_chars = max_tokens * 4
        if len(raw_data) <= max_chars:
            return raw_data
        # Cắt bớt và bổ sung ghi chú nén
        return raw_data[:max_chars] + "\n...[Context compressed due to token budget limit]..."
