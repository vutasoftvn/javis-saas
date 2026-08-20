from typing import List, Dict, Any, Tuple
from app.workforce.agents.profiles.schemas import AgentProfile
from app.workforce.composition.contracts import ResolvedProfile, ProfileExplanation
from app.workforce.agents.runtime.execution_scope import ExecutionScope

class ProfileCompositionService:
    def __init__(self):
        # Dependencies like ExtensionRegistry, ToolRegistry would be injected here
        pass
        
    def resolve(self, profile: AgentProfile, scope: ExecutionScope) -> ResolvedProfile:
        """
        Biên dịch profile gốc thành profile có thể chạy (ResolvedProfile) 
        dựa trên ExecutionScope.
        """
        visible_tools = []
        explanations = []
        
        for tool_id in profile.tools:
            # Check Extension Registry
            if tool_id.startswith("ext."):
                # Mock: giả sử mọi extension mặc định bị disable nếu chưa được cấu hình
                explanations.append(ProfileExplanation(
                    item_id=tool_id,
                    item_type="tool",
                    reason_code="EXTENSION_DISABLED",
                    message=f"Extension for {tool_id} is not enabled in this workspace."
                ))
                continue
                
            # Check Scope Grants
            # Thường tool_id có mapping với required_grants. Ở đây đơn giản hoá logic mock.
            if tool_id == "crm.read" and "crm.read" not in scope.grants:
                explanations.append(ProfileExplanation(
                    item_id=tool_id,
                    item_type="tool",
                    reason_code="SCOPE",
                    message="ExecutionScope lacks crm.read grant."
                ))
                continue
                
            # Nếu hợp lệ
            visible_tools.append(tool_id)

        # Trả về kết quả
        return ResolvedProfile(
            base_profile=profile,
            visible_tool_ids=visible_tools,
            active_skill_versions={},  # Placeholder cho skills
            workflow_permissions=profile.workflows,
            effective_model_policy=profile.model_policy,
            scope_ceiling={"grants": list(scope.grants)},
            approval_baseline={},
            explanations=explanations
        )
