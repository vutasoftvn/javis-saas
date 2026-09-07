"""Task 2 (plan 2026-09-07-local-first-model-routing) — `ModelProviderFactory`:
ánh xạ `ResolvedModelRoute.provider_type` -> adapter cụ thể; validate allowlist
model + credential thuộc đúng workspace TRƯỚC khi build client; CLI providers
(claude_cli/codex_cli/gemini_cli) chưa triển khai (Task 3)."""

from __future__ import annotations

import asyncio
import base64
import os

import pytest
from pydantic import SecretStr

from apps.cosa.models.contracts import ProviderType, ResolvedModelRoute
from apps.cosa.models.credential_store import InMemoryCredentialRepository, LocalCredentialStore
from apps.cosa.models.providers import ModelProviderFactory, ModelProviderMisconfigured


def route(
    *,
    provider_type: ProviderType,
    credential_id: str | None,
    model_id: str = "some-model",
    allowed_models: tuple[str, ...] = (),
    base_url: str | None = None,
) -> ResolvedModelRoute:
    return ResolvedModelRoute(
        workspace_id="ws-a",
        agent_spec_id="cosa.agents.operations",
        profile_id="profile-1",
        provider_type=provider_type,
        model_id=model_id,
        credential_ref=credential_id,
        base_url=base_url,
        allowed_models=allowed_models,
        fallback_profile_ids=(),
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
