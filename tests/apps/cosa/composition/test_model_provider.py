from __future__ import annotations

import base64
import os

import pytest


def test_build_deepseek_model_returns_fake_sdk_model_when_provider_fake(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("COSA_MODEL_PROVIDER", "fake")
    from agent_testkit.fake_sdk_model import FakeSDKModel
    from apps.cosa.composition.model_provider import build_deepseek_model

    model = build_deepseek_model()
    assert isinstance(model, FakeSDKModel)


def test_build_deepseek_model_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("COSA_MODEL_PROVIDER", raising=False)
    from apps.cosa.composition.model_provider import build_deepseek_model

    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        build_deepseek_model()


def test_build_deepseek_model_returns_litellm_model_with_env_config(monkeypatch):
    pytest.importorskip("agents")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-123")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://custom.deepseek.example")
    monkeypatch.setenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-reasoner")
    from agents.extensions.models.litellm_model import LitellmModel
    from apps.cosa.composition.model_provider import build_deepseek_model

    model = build_deepseek_model()

    assert isinstance(model, LitellmModel)


def test_build_credential_store_uses_postgres_repository(tmp_path, monkeypatch):
    """`build_credential_store()` phải luôn wire `PostgresCredentialRepository`
    (không silently rơi về InMemory ở composition root) — session_factory là
    duck-typed nên chỉ cần assert đúng loại repository/store được dựng."""
    key_path = tmp_path / "local_secrets.key"
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(base64.b64encode(os.urandom(32)).decode())
    monkeypatch.setenv("COSA_LOCAL_SECRETS_KEY_FILE", str(key_path))

    from apps.cosa.composition.model_provider import build_credential_store
    from apps.cosa.models.credential_store import LocalCredentialStore, PostgresCredentialRepository

    store = build_credential_store(session_factory=object())

    assert isinstance(store, LocalCredentialStore)
    assert isinstance(store._repo, PostgresCredentialRepository)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_create_workspace_model_client_never_reads_deepseek_env_for_workspace_route(
    tmp_path, monkeypatch
):
    """Route workspace-scoped (Task 1 resolver output) phải build client từ
    `credential_ref` trong credential store — không đọc DEEPSEEK_API_KEY hay
    bất kỳ provider env nào (constraint toàn cục của plan)."""
    pytest.importorskip("agents")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    key_path = tmp_path / "local_secrets.key"
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(base64.b64encode(os.urandom(32)).decode())
    monkeypatch.setenv("COSA_LOCAL_SECRETS_KEY_FILE", str(key_path))

    from pydantic import SecretStr

    from apps.cosa.composition.model_provider import create_workspace_model_client
    from apps.cosa.models.contracts import ProviderType, ResolvedModelRoute
    from apps.cosa.models.credential_store import InMemoryCredentialRepository, LocalCredentialStore

    store = LocalCredentialStore(InMemoryCredentialRepository(), key_file_path=str(key_path))
    ref = await store.put("ws-a", SecretStr("sk-workspace-real-key"))

    monkeypatch.setattr(
        "apps.cosa.composition.model_provider.build_credential_store",
        lambda session_factory: store,
    )

    route = ResolvedModelRoute(
        workspace_id="ws-a",
        agent_spec_id="cosa.agents.operations",
        profile_id="profile-1",
        provider_type=ProviderType.DEEPSEEK_API,
        model_id="deepseek-chat",
        credential_ref=ref.id,
        allowed_models=(),
        fallback_profile_ids=(),
    )

    client = await create_workspace_model_client(route, session_factory=object())

    from agents.extensions.models.litellm_model import LitellmModel

    assert isinstance(client, LitellmModel)


def test_build_deepseek_model_defaults_base_url_and_model(monkeypatch):
    pytest.importorskip("agents")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-123")
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("DEEPSEEK_DEFAULT_MODEL", raising=False)
    from agents.extensions.models.litellm_model import LitellmModel
    from apps.cosa.composition.model_provider import build_deepseek_model

    model = build_deepseek_model()

    assert isinstance(model, LitellmModel)
