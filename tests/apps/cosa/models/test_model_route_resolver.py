"""Task 1 (plan 2026-09-07-local-first-model-routing) — precedence
(AGENT_PROFILE override > WORKSPACE default > system default) và cách ly
workspace cho `ModelRouteResolver`. Dùng `InMemoryModelRoutingRepository`
(không cần Postgres thật — cùng nguyên tắc test khác trong repo dùng
InMemory* cho unit test resolver/repository logic)."""

from __future__ import annotations

import pytest

from apps.cosa.models.contracts import (
    ModelRouteNotFound,
    ProfileStatus,
    ProviderType,
    ResolvedModelRoute,
    SystemDefaultModelProfile,
)
from apps.cosa.models.repository import InMemoryModelRoutingRepository
from apps.cosa.models.resolver import ModelRouteResolver

pytestmark = pytest.mark.asyncio

SYSTEM_DEFAULT = SystemDefaultModelProfile(
    profile_id="system-default",
    provider_type=ProviderType.LOCAL_OPENAI_COMPATIBLE,
    model_id="local-general-model",
    credential_ref=None,
    allowed_models=("local-general-model",),
)


@pytest.fixture
def resolver() -> ModelRouteResolver:
    return ModelRouteResolver(InMemoryModelRoutingRepository(), SYSTEM_DEFAULT)


async def test_agent_override_beats_workspace_default(resolver: ModelRouteResolver) -> None:
    await resolver.create_profile("ws-a", "local-general", ProviderType.LOCAL_OPENAI_COMPATIBLE)
    await resolver.create_profile("ws-a", "claude-fast", ProviderType.ANTHROPIC_API)
    await resolver.set_workspace_default("ws-a", "local-general")
    await resolver.set_agent_override("ws-a", "cosa.agents.operations", "claude-fast", [])

    route = await resolver.resolve_route("ws-a", "cosa.agents.operations")

    assert route.profile_id == "claude-fast"
    assert route.provider_type == ProviderType.ANTHROPIC_API


async def test_workspace_default_used_when_no_override(resolver: ModelRouteResolver) -> None:
    await resolver.create_profile("ws-a", "local-general", ProviderType.LOCAL_OPENAI_COMPATIBLE)
    await resolver.set_workspace_default("ws-a", "local-general")

    route = await resolver.resolve_route("ws-a", "cosa.agents.marketing")

    assert route.profile_id == "local-general"
    # Không có override cho agent_spec khác thì vẫn dùng workspace default,
    # không rơi về system default.
    assert route.profile_id != SYSTEM_DEFAULT.profile_id


async def test_system_default_used_when_workspace_unconfigured(
    resolver: ModelRouteResolver,
) -> None:
    route = await resolver.resolve_route("ws-unconfigured", "cosa.agents.operations")

    assert route.profile_id == SYSTEM_DEFAULT.profile_id
    assert route.provider_type == SYSTEM_DEFAULT.provider_type
    assert route.fallback_profile_ids == ()


async def test_route_never_crosses_workspace(resolver: ModelRouteResolver) -> None:
    await resolver.create_profile("ws-a", "private-route", ProviderType.OPENROUTER_API)

    with pytest.raises(ModelRouteNotFound):
        await resolver.set_workspace_default("ws-b", "private-route")


async def test_agent_override_cannot_reference_other_workspace_profile(
    resolver: ModelRouteResolver,
) -> None:
    await resolver.create_profile("ws-a", "private-route", ProviderType.OPENROUTER_API)

    with pytest.raises(ModelRouteNotFound):
        await resolver.set_agent_override("ws-b", "cosa.agents.operations", "private-route", [])


async def test_fallback_used_when_primary_disabled(resolver: ModelRouteResolver) -> None:
    await resolver.create_profile(
        "ws-a", "flaky-primary", ProviderType.OPENAI_API, status=ProfileStatus.DISABLED
    )
    await resolver.create_profile("ws-a", "healthy-fallback", ProviderType.DEEPSEEK_API)
    await resolver.set_agent_override(
        "ws-a", "cosa.agents.finance", "flaky-primary", ["healthy-fallback"]
    )

    route = await resolver.resolve_route("ws-a", "cosa.agents.finance")

    assert route.profile_id == "healthy-fallback"
    assert route.provider_type == ProviderType.DEEPSEEK_API


async def test_missing_profile_fails_closed_not_silent_default(
    resolver: ModelRouteResolver,
) -> None:
    """Primary profile bị xoá sau khi policy đã set (repository trả None cho
    get_profile) — resolver phải fail-closed, không được âm thầm rơi về
    system default (system default chỉ áp dụng khi hoàn toàn CHƯA có policy)."""
    await resolver.create_profile("ws-a", "temp-profile", ProviderType.CLAUDE_CLI)
    await resolver.set_workspace_default("ws-a", "temp-profile")
    # Xoá thẳng khỏi repo nội bộ để mô phỏng profile bị gỡ sau khi đã pin.
    repo = resolver._repo  # type: ignore[attr-defined]
    del repo._profiles[("ws-a", "temp-profile")]

    with pytest.raises(ModelRouteNotFound):
        await resolver.resolve_route("ws-a", "cosa.agents.operations")


async def test_unapproved_fallback_not_silently_used(resolver: ModelRouteResolver) -> None:
    """Nếu primary bị disable và fallback list không trỏ tới profile hợp lệ
    nào (đã bị gỡ khỏi repo sau khi set_policy), resolver fail-closed thay vì
    trả về route rỗng/mặc định."""
    await resolver.create_profile(
        "ws-a", "disabled-primary", ProviderType.OPENAI_API, status=ProfileStatus.DISABLED
    )
    await resolver.create_profile("ws-a", "will-be-removed", ProviderType.DEEPSEEK_API)
    await resolver.set_agent_override(
        "ws-a", "cosa.agents.support", "disabled-primary", ["will-be-removed"]
    )
    repo = resolver._repo  # type: ignore[attr-defined]
    del repo._profiles[("ws-a", "will-be-removed")]

    with pytest.raises(ModelRouteNotFound):
        await resolver.resolve_route("ws-a", "cosa.agents.support")


async def test_resolved_route_never_contains_secret_field(resolver: ModelRouteResolver) -> None:
    """`ResolvedModelRoute` chỉ được phép có `credential_ref` (ID/reference) —
    `extra="forbid"` chặn field bí mật lạ tại biên contract."""
    await resolver.create_profile(
        "ws-a", "local-general", ProviderType.LOCAL_OPENAI_COMPATIBLE, credential_ref="cred-123"
    )
    await resolver.set_workspace_default("ws-a", "local-general")

    route = await resolver.resolve_route("ws-a", "cosa.agents.operations")

    assert route.credential_ref == "cred-123"
    assert "credential_ref" in ResolvedModelRoute.model_fields
    assert not any(
        name in ResolvedModelRoute.model_fields
        for name in ("api_key", "secret", "credential_value", "token")
    )
    with pytest.raises(ValueError):
        ResolvedModelRoute(**{**route.model_dump(), "api_key": "sk-should-not-exist"})


async def test_base_url_round_trips_through_repository_and_resolver(
    resolver: ModelRouteResolver,
) -> None:
    """`base_url` (fast-follow field cho LOCAL_OPENAI_COMPATIBLE — endpoint tự
    host không phải secret, xem contracts.py) phải sống sót qua
    create_profile() -> repository -> resolve_route(), không bị rớt ở bất kỳ
    tầng nào."""
    await resolver.create_profile(
        "ws-a",
        "local-ollama",
        ProviderType.LOCAL_OPENAI_COMPATIBLE,
        base_url="http://localhost:11434/v1",
    )
    await resolver.set_workspace_default("ws-a", "local-ollama")

    route = await resolver.resolve_route("ws-a", "cosa.agents.operations")

    assert route.base_url == "http://localhost:11434/v1"


async def test_base_url_defaults_to_none_when_not_configured(
    resolver: ModelRouteResolver,
) -> None:
    await resolver.create_profile("ws-a", "claude-fast", ProviderType.ANTHROPIC_API)
    await resolver.set_workspace_default("ws-a", "claude-fast")

    route = await resolver.resolve_route("ws-a", "cosa.agents.operations")

    assert route.base_url is None
