"""Task 1 (plan 2026-09-07-local-first-model-routing) — repository cho
`models.model_provider_profiles` / `models.workspace_model_policies`
(migration `packages/agent/migrations/030_workspace_model_routing.sql`).

Cùng convention với `apps/cosa/knowledge_ingestion/local_repository.py`:
`PostgresModelRoutingRepository` (SQLAlchemy async session_factory, set
`cosa.workspace_id` mỗi transaction để RLS fail-closed áp dụng đúng) và
`InMemoryModelRoutingRepository` (test/dev-only, không persist qua process
restart) implement cùng interface (duck typing, không cần ABC chung).

Cả 2 implementation đều validate: `set_policy()` chỉ chấp nhận
primary/fallback profile_id đã tồn tại trong ĐÚNG workspace đó — một profile
tạo ở workspace khác không bao giờ được set làm default/override/fallback
(chặn route cross-workspace ngay tại lớp ghi, không chỉ ở lớp đọc).
"""

from __future__ import annotations

from typing import Any

from apps.cosa.models.contracts import (
    ModelProviderProfile,
    ModelRouteNotFound,
    PolicyScope,
    ProfileStatus,
    ProviderType,
    WorkspaceModelPolicy,
)

__all__ = [
    "InMemoryModelRoutingRepository",
    "PostgresModelRoutingRepository",
]


class PostgresModelRoutingRepository:
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def _set_workspace(self, session: Any, workspace_id: str) -> None:
        from sqlalchemy import text

        await session.execute(
            text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
            {"workspace_id": workspace_id},
        )

    async def create_profile(
        self,
        workspace_id: str,
        profile_id: str,
        provider_type: ProviderType,
        *,
        model_id: str | None = None,
        credential_ref: str | None = None,
        base_url: str | None = None,
        allowed_models: tuple[str, ...] = (),
        budget_usd_limit: float | None = None,
        max_concurrency: int | None = None,
        status: ProfileStatus = ProfileStatus.ACTIVE,
    ) -> ModelProviderProfile:
        import json as _json

        from sqlalchemy import text

        resolved_model_id = model_id or profile_id
        async with self._session_factory() as session:
            await self._set_workspace(session, workspace_id)
            await session.execute(
                text(
                    """
                    INSERT INTO models.model_provider_profiles (
                        workspace_id, profile_id, provider_type, model_id,
                        credential_ref, base_url, allowed_models, budget_usd_limit,
                        max_concurrency, status
                    ) VALUES (
                        :workspace_id, :profile_id, :provider_type, :model_id,
                        :credential_ref, :base_url, :allowed_models, :budget_usd_limit,
                        :max_concurrency, :status
                    )
                    ON CONFLICT (workspace_id, profile_id) DO UPDATE SET
                        provider_type = EXCLUDED.provider_type,
                        model_id = EXCLUDED.model_id,
                        credential_ref = EXCLUDED.credential_ref,
                        base_url = EXCLUDED.base_url,
                        allowed_models = EXCLUDED.allowed_models,
                        budget_usd_limit = EXCLUDED.budget_usd_limit,
                        max_concurrency = EXCLUDED.max_concurrency,
                        status = EXCLUDED.status,
                        updated_at = now()
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "profile_id": profile_id,
                    "provider_type": provider_type.value,
                    "model_id": resolved_model_id,
                    "credential_ref": credential_ref,
                    "base_url": base_url,
                    "allowed_models": _json.dumps(list(allowed_models)),
                    "budget_usd_limit": budget_usd_limit,
                    "max_concurrency": max_concurrency,
                    "status": status.value,
                },
            )
            await session.commit()
        return ModelProviderProfile(
            workspace_id=workspace_id,
            profile_id=profile_id,
            provider_type=provider_type,
            model_id=resolved_model_id,
            credential_ref=credential_ref,
            base_url=base_url,
            allowed_models=tuple(allowed_models),
            budget_usd_limit=budget_usd_limit,
            max_concurrency=max_concurrency,
            status=status,
        )

    async def get_profile(self, workspace_id: str, profile_id: str) -> ModelProviderProfile | None:
        from sqlalchemy import text

        async with self._session_factory() as session:
            await self._set_workspace(session, workspace_id)
            res = await session.execute(
                text(
                    """
                    SELECT workspace_id, profile_id, provider_type, model_id,
                           credential_ref, base_url, allowed_models, budget_usd_limit,
                           max_concurrency, status
                    FROM models.model_provider_profiles
                    WHERE workspace_id = :workspace_id AND profile_id = :profile_id
                    """
                ),
                {"workspace_id": workspace_id, "profile_id": profile_id},
            )
            row = res.mappings().first()
            if row is None:
                return None
            return ModelProviderProfile(
                workspace_id=row["workspace_id"],
                profile_id=row["profile_id"],
                provider_type=ProviderType(row["provider_type"]),
                model_id=row["model_id"],
                credential_ref=row["credential_ref"],
                base_url=row["base_url"],
                allowed_models=tuple(row["allowed_models"] or []),
                budget_usd_limit=(
                    float(row["budget_usd_limit"]) if row["budget_usd_limit"] is not None else None
                ),
                max_concurrency=row["max_concurrency"],
                status=ProfileStatus(row["status"]),
            )

    async def set_policy(
        self,
        workspace_id: str,
        scope: PolicyScope,
        scope_key: str,
        primary_profile_id: str,
        fallback_profile_ids: tuple[str, ...] = (),
    ) -> WorkspaceModelPolicy:
        import json as _json

        from sqlalchemy import text

        # Fail-closed: primary/fallback phải tồn tại ĐÚNG trong workspace này —
        # không bao giờ set policy trỏ tới profile của workspace khác.
        primary = await self.get_profile(workspace_id, primary_profile_id)
        if primary is None:
            raise ModelRouteNotFound(
                f"Profile '{primary_profile_id}' không tồn tại trong workspace "
                f"'{workspace_id}' — không thể set làm primary route."
            )
        for fallback_id in fallback_profile_ids:
            if await self.get_profile(workspace_id, fallback_id) is None:
                raise ModelRouteNotFound(
                    f"Fallback profile '{fallback_id}' không tồn tại trong "
                    f"workspace '{workspace_id}'."
                )

        async with self._session_factory() as session:
            await self._set_workspace(session, workspace_id)
            await session.execute(
                text(
                    """
                    INSERT INTO models.workspace_model_policies (
                        workspace_id, scope, scope_key, primary_profile_id,
                        fallback_profile_ids
                    ) VALUES (
                        :workspace_id, :scope, :scope_key, :primary_profile_id,
                        :fallback_profile_ids
                    )
                    ON CONFLICT (workspace_id, scope, scope_key) DO UPDATE SET
                        primary_profile_id = EXCLUDED.primary_profile_id,
                        fallback_profile_ids = EXCLUDED.fallback_profile_ids,
                        updated_at = now()
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "scope": scope.value,
                    "scope_key": scope_key,
                    "primary_profile_id": primary_profile_id,
                    "fallback_profile_ids": _json.dumps(list(fallback_profile_ids)),
                },
            )
            await session.commit()
        return WorkspaceModelPolicy(
            workspace_id=workspace_id,
            scope=scope,
            scope_key=scope_key,
            primary_profile_id=primary_profile_id,
            fallback_profile_ids=tuple(fallback_profile_ids),
        )

    async def get_policy(
        self, workspace_id: str, scope: PolicyScope, scope_key: str
    ) -> WorkspaceModelPolicy | None:
        from sqlalchemy import text

        async with self._session_factory() as session:
            await self._set_workspace(session, workspace_id)
            res = await session.execute(
                text(
                    """
                    SELECT workspace_id, scope, scope_key, primary_profile_id,
                           fallback_profile_ids
                    FROM models.workspace_model_policies
                    WHERE workspace_id = :workspace_id AND scope = :scope
                      AND scope_key = :scope_key
                    """
                ),
                {"workspace_id": workspace_id, "scope": scope.value, "scope_key": scope_key},
            )
            row = res.mappings().first()
            if row is None:
                return None
            return WorkspaceModelPolicy(
                workspace_id=row["workspace_id"],
                scope=PolicyScope(row["scope"]),
                scope_key=row["scope_key"],
                primary_profile_id=row["primary_profile_id"],
                fallback_profile_ids=tuple(row["fallback_profile_ids"] or []),
            )


class InMemoryModelRoutingRepository:
    """Test/dev-only — không persist qua process restart. Cùng interface với
    `PostgresModelRoutingRepository` (duck typing, cùng nguyên tắc InMemory*
    khác trong repo, vd. `InMemoryLocalIngestionRepository`)."""

    def __init__(self) -> None:
        self._profiles: dict[tuple[str, str], ModelProviderProfile] = {}
        self._policies: dict[tuple[str, PolicyScope, str], WorkspaceModelPolicy] = {}

    async def create_profile(
        self,
        workspace_id: str,
        profile_id: str,
        provider_type: ProviderType,
        *,
        model_id: str | None = None,
        credential_ref: str | None = None,
        base_url: str | None = None,
        allowed_models: tuple[str, ...] = (),
        budget_usd_limit: float | None = None,
        max_concurrency: int | None = None,
        status: ProfileStatus = ProfileStatus.ACTIVE,
    ) -> ModelProviderProfile:
        profile = ModelProviderProfile(
            workspace_id=workspace_id,
            profile_id=profile_id,
            provider_type=provider_type,
            model_id=model_id or profile_id,
            credential_ref=credential_ref,
            base_url=base_url,
            allowed_models=tuple(allowed_models),
            budget_usd_limit=budget_usd_limit,
            max_concurrency=max_concurrency,
            status=status,
        )
        self._profiles[(workspace_id, profile_id)] = profile
        return profile

    async def get_profile(self, workspace_id: str, profile_id: str) -> ModelProviderProfile | None:
        return self._profiles.get((workspace_id, profile_id))

    async def set_policy(
        self,
        workspace_id: str,
        scope: PolicyScope,
        scope_key: str,
        primary_profile_id: str,
        fallback_profile_ids: tuple[str, ...] = (),
    ) -> WorkspaceModelPolicy:
        if await self.get_profile(workspace_id, primary_profile_id) is None:
            raise ModelRouteNotFound(
                f"Profile '{primary_profile_id}' không tồn tại trong workspace "
                f"'{workspace_id}' — không thể set làm primary route."
            )
        for fallback_id in fallback_profile_ids:
            if await self.get_profile(workspace_id, fallback_id) is None:
                raise ModelRouteNotFound(
                    f"Fallback profile '{fallback_id}' không tồn tại trong "
                    f"workspace '{workspace_id}'."
                )
        policy = WorkspaceModelPolicy(
            workspace_id=workspace_id,
            scope=scope,
            scope_key=scope_key,
            primary_profile_id=primary_profile_id,
            fallback_profile_ids=tuple(fallback_profile_ids),
        )
        self._policies[(workspace_id, scope, scope_key)] = policy
        return policy

    async def get_policy(
        self, workspace_id: str, scope: PolicyScope, scope_key: str
    ) -> WorkspaceModelPolicy | None:
        return self._policies.get((workspace_id, scope, scope_key))
