"""Task 1 (plan 2026-09-07-local-first-model-routing) — resolve model route
theo thứ tự ưu tiên xác định: AGENT_PROFILE override > WORKSPACE default >
system default injected. Không đọc env (`DEEPSEEK_*` hay bất kỳ provider env
nào) để chọn route theo workspace — env chỉ được phép bootstrap 1 system
default hoặc test double, do caller tiêm vào qua `system_default`.

Fallback CHỈ là allowlist tường minh đã lưu trên policy
(`WorkspaceModelPolicy.fallback_profile_ids`) — resolver không tự suy ra
fallback nào khác. Một fallback profile không tồn tại/không ACTIVE trong
đúng workspace bị bỏ qua (không dùng); nếu primary lẫn toàn bộ fallback đều
không hợp lệ, resolver fail-closed bằng `ModelRouteNotFound` thay vì âm thầm
rơi về 1 model mặc định ngoài ý muốn.
"""

from __future__ import annotations

from typing import Any

from apps.cosa.models.contracts import (
    ModelRouteNotFound,
    PolicyScope,
    ProfileStatus,
    ProviderType,
    ResolvedModelRoute,
    SystemDefaultModelProfile,
    WorkspaceModelPolicy,
)

__all__ = ["ModelRouteResolver"]


class ModelRouteResolver:
    def __init__(self, repository: Any, system_default: SystemDefaultModelProfile) -> None:
        self._repo = repository
        self._system_default = system_default

    # ── Composition tiện dụng cho caller/test — uỷ quyền thẳng xuống repository ──

    async def create_profile(
        self,
        workspace_id: str,
        profile_id: str,
        provider_type: ProviderType,
        **kwargs: Any,
    ):
        return await self._repo.create_profile(workspace_id, profile_id, provider_type, **kwargs)

    async def set_workspace_default(
        self, workspace_id: str, profile_id: str
    ) -> WorkspaceModelPolicy:
        return await self._repo.set_policy(
            workspace_id,
            PolicyScope.WORKSPACE,
            workspace_id,
            profile_id,
            (),
        )

    async def set_agent_override(
        self,
        workspace_id: str,
        agent_spec_id: str,
        profile_id: str,
        fallback_profile_ids: tuple[str, ...] | list[str] = (),
    ) -> WorkspaceModelPolicy:
        return await self._repo.set_policy(
            workspace_id,
            PolicyScope.AGENT_PROFILE,
            agent_spec_id,
            profile_id,
            tuple(fallback_profile_ids),
        )

    # ── Resolve chính ──

    async def resolve_route(self, workspace_id: str, agent_spec_id: str) -> ResolvedModelRoute:
        policy = await self._repo.get_policy(workspace_id, PolicyScope.AGENT_PROFILE, agent_spec_id)
        policy = policy or await self._repo.get_policy(
            workspace_id, PolicyScope.WORKSPACE, workspace_id
        )
        return await self._validate(workspace_id, agent_spec_id, policy)

    async def _validate(
        self,
        workspace_id: str,
        agent_spec_id: str,
        policy: WorkspaceModelPolicy | None,
    ) -> ResolvedModelRoute:
        if policy is None:
            sd = self._system_default
            return ResolvedModelRoute(
                workspace_id=workspace_id,
                agent_spec_id=agent_spec_id,
                profile_id=sd.profile_id,
                provider_type=sd.provider_type,
                model_id=sd.model_id,
                credential_ref=sd.credential_ref,
                base_url=sd.base_url,
                allowed_models=sd.allowed_models,
                fallback_profile_ids=(),
            )

        for candidate_id in (policy.primary_profile_id, *policy.fallback_profile_ids):
            profile = await self._repo.get_profile(workspace_id, candidate_id)
            if profile is not None and profile.status == ProfileStatus.ACTIVE:
                return ResolvedModelRoute(
                    workspace_id=workspace_id,
                    agent_spec_id=agent_spec_id,
                    profile_id=profile.profile_id,
                    provider_type=profile.provider_type,
                    model_id=profile.model_id,
                    credential_ref=profile.credential_ref,
                    base_url=profile.base_url,
                    allowed_models=profile.allowed_models,
                    fallback_profile_ids=policy.fallback_profile_ids,
                )

        raise ModelRouteNotFound(
            f"Không có profile hợp lệ (ACTIVE) cho workspace='{workspace_id}' "
            f"agent_spec='{agent_spec_id}' — primary='{policy.primary_profile_id}', "
            f"fallback={list(policy.fallback_profile_ids)}."
        )
