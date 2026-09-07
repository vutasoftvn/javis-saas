"""Task 2 (plan 2026-09-07-local-first-model-routing) — `ModelProviderFactory`:
ánh xạ `ResolvedModelRoute.provider_type` -> adapter cụ thể; validate allowlist
model + credential thuộc đúng workspace TRƯỚC khi build client; CLI providers
(claude_cli/codex_cli/gemini_cli) chưa triển khai (Task 3)."""

from __future__ import annotations

import asyncio
import base64
import logging
import os

import pytest
from pydantic import SecretStr

from apps.cosa.models.contracts import ProviderType, ResolvedModelRoute
from apps.cosa.models.credential_store import InMemoryCredentialRepository, LocalCredentialStore
from apps.cosa.models.providers import ModelProviderFactory, ModelProviderMisconfigured
from apps.cosa.models.repository import InMemoryModelRoutingRepository


def route(
    *,
    provider_type: ProviderType,
    credential_id: str | None,
    model_id: str = "some-model",
    allowed_models: tuple[str, ...] = (),
    base_url: str | None = None,
    profile_id: str = "profile-1",
    is_system_default: bool = False,
) -> ResolvedModelRoute:
    return ResolvedModelRoute(
        workspace_id="ws-a",
        agent_spec_id="cosa.agents.operations",
        profile_id=profile_id,
        provider_type=provider_type,
        model_id=model_id,
        credential_ref=credential_id,
        base_url=base_url,
        allowed_models=allowed_models,
        fallback_profile_ids=(),
        is_system_default=is_system_default,
    )


@pytest.fixture
def credential_store(tmp_path) -> LocalCredentialStore:
    path = tmp_path / "local_secrets.key"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(base64.b64encode(os.urandom(32)).decode())
    return LocalCredentialStore(InMemoryCredentialRepository(), key_file_path=str(path))


@pytest.fixture
def factory(credential_store: LocalCredentialStore) -> ModelProviderFactory:
    return ModelProviderFactory(credential_store)


def test_openai_api_profile_requires_api_credential(factory: ModelProviderFactory) -> None:
    with pytest.raises(ModelProviderMisconfigured):
        asyncio.run(
            factory.create(route(provider_type=ProviderType.OPENAI_API, credential_id=None))
        )


@pytest.mark.asyncio
async def test_deepseek_api_builds_client_with_resolved_credential(
    factory: ModelProviderFactory, credential_store: LocalCredentialStore
) -> None:
    ref = await credential_store.put("ws-a", SecretStr("sk-deepseek-real-key"))

    client = await factory.create(
        route(
            provider_type=ProviderType.DEEPSEEK_API, credential_id=ref.id, model_id="deepseek-chat"
        )
    )

    assert client is not None
    assert "deepseek" in getattr(client, "model", "").lower()


@pytest.mark.asyncio
async def test_credential_from_other_workspace_is_rejected(
    factory: ModelProviderFactory, credential_store: LocalCredentialStore
) -> None:
    ref = await credential_store.put("ws-other", SecretStr("sk-not-for-ws-a"))

    with pytest.raises(ModelProviderMisconfigured):
        await factory.create(route(provider_type=ProviderType.ANTHROPIC_API, credential_id=ref.id))


@pytest.mark.asyncio
async def test_misconfigured_error_never_contains_plaintext_secret(
    factory: ModelProviderFactory, credential_store: LocalCredentialStore
) -> None:
    ref = await credential_store.put("ws-other", SecretStr("sk-should-never-leak"))

    with pytest.raises(ModelProviderMisconfigured) as exc_info:
        await factory.create(route(provider_type=ProviderType.OPENAI_API, credential_id=ref.id))

    assert "sk-should-never-leak" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_local_openai_compatible_allows_missing_credential(
    factory: ModelProviderFactory,
) -> None:
    client = await factory.create(
        route(provider_type=ProviderType.LOCAL_OPENAI_COMPATIBLE, credential_id=None)
    )

    assert client is not None


@pytest.mark.asyncio
async def test_local_openai_compatible_uses_configured_base_url(
    factory: ModelProviderFactory,
) -> None:
    client = await factory.create(
        route(
            provider_type=ProviderType.LOCAL_OPENAI_COMPATIBLE,
            credential_id=None,
            base_url="http://localhost:11434/v1",
        )
    )

    assert client is not None
    assert getattr(client, "base_url", None) == "http://localhost:11434/v1"


@pytest.mark.asyncio
async def test_allowed_models_enforced_before_client_build(factory: ModelProviderFactory) -> None:
    with pytest.raises(ModelProviderMisconfigured):
        await factory.create(
            route(
                provider_type=ProviderType.LOCAL_OPENAI_COMPATIBLE,
                credential_id=None,
                model_id="not-allowed-model",
                allowed_models=("only-this-model",),
            )
        )


@pytest.mark.parametrize(
    "provider_type",
    [ProviderType.CLAUDE_CLI, ProviderType.CODEX_CLI, ProviderType.GEMINI_CLI],
)
@pytest.mark.asyncio
async def test_cli_providers_not_yet_implemented(
    factory: ModelProviderFactory, provider_type: ProviderType
) -> None:
    with pytest.raises(NotImplementedError):
        await factory.create(route(provider_type=provider_type, credential_id=None))


@pytest.mark.asyncio
async def test_system_default_route_skips_profile_repository_lookup(
    credential_store: LocalCredentialStore,
) -> None:
    """Review finding #1 — 1 route đến từ `SystemDefaultModelProfile`
    (`is_system_default=True`) không có row nào trong
    `models.model_provider_profiles`. Nếu factory được tiêm 1
    `profile_repository` thật (vd Postgres) cho 1 workspace hoàn toàn chưa
    cấu hình gì, `get_profile()` sẽ luôn trả None cho profile_id đó —
    `_validate_profile_limits` PHẢI skip tra cứu cho case này, không được
    hiểu lầm None thành "profile đã bị xoá" và từ chối oan route hợp lệ."""
    profile_repository = InMemoryModelRoutingRepository()  # cố tình KHÔNG tạo profile nào
    factory = ModelProviderFactory(credential_store, profile_repository=profile_repository)

    client = await factory.create(
        route(
            provider_type=ProviderType.LOCAL_OPENAI_COMPATIBLE,
            credential_id=None,
            profile_id="system-default",
            is_system_default=True,
        )
    )

    assert client is not None


@pytest.mark.asyncio
async def test_non_system_default_route_with_missing_profile_is_still_rejected(
    credential_store: LocalCredentialStore,
) -> None:
    """Đối chứng cho test trên: 1 route KHÔNG phải system-default nhưng
    profile đã bị xoá khỏi repository (race giữa lúc resolve và lúc build
    client) vẫn phải bị từ chối như cũ — fix cho finding #1 chỉ skip đúng
    case system-default, không làm yếu check profile-bị-xoá nói chung."""
    profile_repository = InMemoryModelRoutingRepository()
    factory = ModelProviderFactory(credential_store, profile_repository=profile_repository)

    with pytest.raises(ModelProviderMisconfigured):
        await factory.create(
            route(
                provider_type=ProviderType.LOCAL_OPENAI_COMPATIBLE,
                credential_id=None,
                profile_id="deleted-profile",
                is_system_default=False,
            )
        )


@pytest.mark.asyncio
async def test_adapter_construction_failure_logs_redacted_payload_and_wraps_error(
    factory: ModelProviderFactory,
    credential_store: LocalCredentialStore,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Review finding #3 — `redact_provider_payload` phải được gọi từ 1 call
    site thật (không chỉ test của chính nó): khi adapter construction bên
    dưới (litellm/agents SDK) raise 1 exception bất ngờ, factory phải log
    diagnostic đã redact TRƯỚC khi wrap thành `ModelProviderMisconfigured` —
    không để plaintext (kể cả lọt vào message lỗi của SDK khác) tới log."""
    ref = await credential_store.put("ws-a", SecretStr("sk-should-not-reach-log-plaintext"))

    def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("sdk exploded, key was sk-should-not-reach-log-plaintext-token")

    monkeypatch.setattr("agents.extensions.models.litellm_model.LitellmModel", _boom)

    with (
        caplog.at_level(logging.ERROR, logger="apps.cosa.models.providers"),
        pytest.raises(ModelProviderMisconfigured),
    ):
        await factory.create(route(provider_type=ProviderType.DEEPSEEK_API, credential_id=ref.id))

    assert caplog.records, "expected a diagnostic log record from the construction failure path"
    logged_text = " ".join(record.getMessage() for record in caplog.records)
    assert "sk-should-not-reach-log-plaintext-token" not in logged_text
    assert "sk-should-not-reach-log-plaintext" not in logged_text
