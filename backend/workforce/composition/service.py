from sqlalchemy.orm import Session

from workforce.agents.profiles.schemas import AgentProfile
from workforce.agents.runtime.execution_scope import ExecutionScope
from workforce.composition.contracts import ProfileExplanation, ResolvedProfile
from workforce.extensions.eligibility import (
    EligibleCapability,
    resolve_eligible_capabilities,
)
from workforce.extensions.registry import ExtensionRegistry
from workforce.extensions.tool_registration import extension_tool_spec

class ProfileCompositionService:
    def __init__(self, extension_registry: ExtensionRegistry | None = None):
        self._extension_registry = extension_registry or ExtensionRegistry()

    def resolve(
        self,
        profile: AgentProfile,
        scope: ExecutionScope,
        db: Session,
    ) -> ResolvedProfile:
        """Compile a profile against the current scope and extension snapshots.

        Skill activation intentionally remains empty: its version/lifecycle audit
        is separate from this extension-tool eligibility composition.
        """
        extension_capabilities = self._extension_capability_index(db, scope)
        visible_tools = []
        explanations = []
        
        for tool_id in profile.tools:
            if tool_id.startswith("ext."):
                capability = extension_capabilities.get(tool_id)
                if capability is None:
                    explanations.append(ProfileExplanation(
                        item_id=tool_id,
                        item_type="tool",
                        reason_code="EXTENSION_UNAVAILABLE",
                        message=f"Extension tool {tool_id} is unavailable in this scope.",
                    ))
                elif capability.eligible:
                    visible_tools.append(tool_id)
                else:
                    explanations.append(ProfileExplanation(
                        item_id=tool_id,
                        item_type="tool",
                        reason_code=capability.reason_code or "EXTENSION_UNAVAILABLE",
                        message=f"Extension tool {tool_id} is unavailable in this scope.",
                    ))
                continue
                
            if tool_id in profile.permissions and tool_id not in scope.grants:
                explanations.append(ProfileExplanation(
                    item_id=tool_id,
                    item_type="tool",
                    reason_code="SCOPE",
                    message=f"ExecutionScope lacks {tool_id} grant."
                ))
                continue
                
            visible_tools.append(tool_id)

        return ResolvedProfile(
            base_profile=profile,
            visible_tool_ids=visible_tools,
            active_skill_versions={},
            workflow_permissions=profile.workflows,
            effective_model_policy=profile.model_policy,
            scope_ceiling={"grants": list(scope.grants)},
            approval_baseline={},
            explanations=explanations
        )

    def _extension_capability_index(
        self, db: Session, scope: ExecutionScope
    ) -> dict[str, EligibleCapability]:
        index = {}
        for eligible in resolve_eligible_capabilities(db, scope):
            registration = self._extension_registry.get(
                db, scope.workspace_id, eligible.extension_id
            )
            capability = self._extension_registry.get_capability(
                db, scope.workspace_id, eligible.capability_id
            )
            if registration is None or capability is None:
                continue

            canonical_tool_id = extension_tool_spec(
                eligible, capability, registration.manifest_jsonb
            ).flat_name
            index[f"ext.{canonical_tool_id}"] = eligible
        return index
