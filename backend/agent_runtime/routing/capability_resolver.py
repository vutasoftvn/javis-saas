"""
COSA Capability Resolver Implementation
Lựa chọn và phối hợp Capabilities (Skills, Tools, Workflows) dựa trên Intent và Agent Profile (Structure.md Mục 14).
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from agent_runtime.profiles.schema import AgentProfile
from agent_runtime.routing.base import IntentClassificationResult


class ResolvedCapabilities(BaseModel):
    """Tập hợp năng lực đã được chọn lọc và kiểm tra phân quyền"""
    profile_id: str
    active_skills: List[str] = Field(default_factory=list)
    executable_tools: List[str] = Field(default_factory=list)
    selected_workflow_id: Optional[str] = None
    reasoning: str = ""


class CapabilityResolver:
    """Bộ phân giải năng lực của Co-founder Orchestrator"""

    @staticmethod
    def resolve(
        intent_result: IntentClassificationResult,
        profile: AgentProfile,
        available_tools: Optional[List[str]] = None
    ) -> ResolvedCapabilities:
        """Đối chiếu intent với Agent Profile để chọn lọc Tools và Skills được phép dùng"""
        available = set(available_tools) if available_tools else set(profile.tools)

        # 1. Nếu là Greeting hoặc General Chat -> Không cấp Tool để tránh side-effects
        if intent_result.category.value in ("conversation.greeting", "conversation.general"):
            return ResolvedCapabilities(
                profile_id=profile.id,
                active_skills=[],
                executable_tools=[],
                selected_workflow_id=None,
                reasoning="Conversation intent requires zero tools"
            )

        # 2. Lọc Skills: Giao giữa suggested_skills và profile.skills (hoặc lấy toàn bộ profile.skills nếu không gợi ý)
        matched_skills = []
        if intent_result.suggested_skills:
            matched_skills = [s for s in intent_result.suggested_skills if s in profile.skills]
        if not matched_skills and profile.skills:
            matched_skills = profile.skills[:2]

        # 3. Lọc Tools: Giao giữa suggested_tools và profile.tools được phép
        matched_tools = []
        if intent_result.suggested_tools:
            matched_tools = [t for t in intent_result.suggested_tools if t in profile.tools and t in available]
        if not matched_tools and profile.tools:
            matched_tools = [t for t in profile.tools if t in available]

        # 4. Lọc Workflow: Kiểm tra workflow có nằm trong profile.workflows không
        workflow_id = None
        if intent_result.suggested_workflow_id and intent_result.suggested_workflow_id in profile.workflows:
            workflow_id = intent_result.suggested_workflow_id

        return ResolvedCapabilities(
            profile_id=profile.id,
            active_skills=matched_skills,
            executable_tools=matched_tools,
            selected_workflow_id=workflow_id,
            reasoning=f"Resolved {len(matched_tools)} tools and {len(matched_skills)} skills for intent {intent_result.category.value}"
        )
