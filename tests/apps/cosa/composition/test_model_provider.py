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


# ── build_system_default_model() / system_default_model_configured() /
# system_default_model_identity() (side task 2026-09-27 — OpenRouter làm
# system-default model provider) ──


def _clear_default_provider_env(monkeypatch):
    monkeypatch.delenv("COSA_DEFAULT_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("COSA_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)


def test_build_system_default_model_defaults_to_deepseek_when_unset(monkeypatch):
    """Không đặt COSA_DEFAULT_MODEL_PROVIDER -> giữ hành vi cũ (deepseek),
    không đổi ngầm môi trường khác chưa cấu hình biến này."""
    pytest.importorskip("agents")
    _clear_default_provider_env(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-123")
    from agents.extensions.models.litellm_model import LitellmModel
    from apps.cosa.composition.model_provider import build_system_default_model

    model = build_system_default_model()

    assert isinstance(model, LitellmModel)
    assert model.model == "deepseek/deepseek-chat"


def test_build_system_default_model_openrouter_requires_api_key(monkeypatch):
    _clear_default_provider_env(monkeypatch)
    monkeypatch.setenv("COSA_DEFAULT_MODEL_PROVIDER", "openrouter")
    from apps.cosa.composition.model_provider import build_system_default_model

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        build_system_default_model()


def test_build_system_default_model_openrouter_builds_litellm_model(monkeypatch):
    pytest.importorskip("agents")
    _clear_default_provider_env(monkeypatch)
    monkeypatch.setenv("COSA_DEFAULT_MODEL_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-fake-key-123")
    monkeypatch.setenv("OPENROUTER_DEFAULT_MODEL", "inclusionai/ling-3.0-flash-fin:free")
    from agents.extensions.models.litellm_model import LitellmModel
    from apps.cosa.composition.model_provider import build_system_default_model

    model = build_system_default_model()

    assert isinstance(model, LitellmModel)
    assert model.model == "openrouter/inclusionai/ling-3.0-flash-fin:free"


def test_build_system_default_model_unknown_provider_raises(monkeypatch):
    _clear_default_provider_env(monkeypatch)
    monkeypatch.setenv("COSA_DEFAULT_MODEL_PROVIDER", "bogus-provider")
    from apps.cosa.composition.model_provider import build_system_default_model

    with pytest.raises(RuntimeError, match="bogus-provider"):
        build_system_default_model()


def test_build_system_default_model_fake_provider_short_circuits(monkeypatch):
    _clear_default_provider_env(monkeypatch)
    monkeypatch.setenv("COSA_DEFAULT_MODEL_PROVIDER", "openrouter")
    monkeypatch.setenv("COSA_MODEL_PROVIDER", "fake")
    from agent_testkit.fake_sdk_model import FakeSDKModel
    from apps.cosa.composition.model_provider import build_system_default_model

    model = build_system_default_model()

    assert isinstance(model, FakeSDKModel)


def test_system_default_model_configured_false_without_key(monkeypatch):
    _clear_default_provider_env(monkeypatch)
    monkeypatch.setenv("COSA_DEFAULT_MODEL_PROVIDER", "openrouter")
    from apps.cosa.composition.model_provider import system_default_model_configured

    assert system_default_model_configured() is False


def test_system_default_model_configured_true_with_openrouter_key(monkeypatch):
    _clear_default_provider_env(monkeypatch)
    monkeypatch.setenv("COSA_DEFAULT_MODEL_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-fake-key-123")
    from apps.cosa.composition.model_provider import system_default_model_configured

    assert system_default_model_configured() is True


def test_system_default_model_configured_deepseek_default(monkeypatch):
    _clear_default_provider_env(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-123")
    from apps.cosa.composition.model_provider import system_default_model_configured

    assert system_default_model_configured() is True


def test_system_default_model_configured_unknown_provider_raises(monkeypatch):
    """Trước fix: giá trị lạ ở COSA_DEFAULT_MODEL_PROVIDER khiến
    system_default_model_configured() trả False (không raise) trong khi
    build_system_default_model()/system_default_model_identity() raise —
    invariant ngầm bị vi phạm, caller `if not system_default_model_configured():
    use FakeSDKModel` (worker/main.py, api/test_main.py) sẽ âm thầm rơi về
    FakeSDKModel thay vì fail-closed. Cả ba hàm giờ dùng chung
    _resolve_system_default_provider() -> phải cùng raise RuntimeError."""
    _clear_default_provider_env(monkeypatch)
    monkeypatch.setenv("COSA_DEFAULT_MODEL_PROVIDER", "bogus-provider")
    from apps.cosa.composition.model_provider import system_default_model_configured

    with pytest.raises(RuntimeError, match="bogus-provider"):
        system_default_model_configured()


def test_system_default_model_identity_openrouter(monkeypatch):
    _clear_default_provider_env(monkeypatch)
    monkeypatch.setenv("COSA_DEFAULT_MODEL_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_DEFAULT_MODEL", "inclusionai/ling-3.0-flash-fin:free")
    from apps.cosa.composition.model_provider import system_default_model_identity
    from apps.cosa.models.contracts import ProviderType

    provider_type, model_id = system_default_model_identity()

    assert provider_type == ProviderType.OPENROUTER_API
    assert model_id == "inclusionai/ling-3.0-flash-fin:free"


def test_system_default_model_identity_deepseek_default(monkeypatch):
    _clear_default_provider_env(monkeypatch)
    from apps.cosa.composition.model_provider import system_default_model_identity
    from apps.cosa.models.contracts import ProviderType

    provider_type, model_id = system_default_model_identity()

    assert provider_type == ProviderType.DEEPSEEK_API
    assert model_id == "deepseek-chat"


def test_system_default_model_identity_unknown_provider_raises(monkeypatch):
    _clear_default_provider_env(monkeypatch)
    monkeypatch.setenv("COSA_DEFAULT_MODEL_PROVIDER", "bogus-provider")
    from apps.cosa.composition.model_provider import system_default_model_identity

    with pytest.raises(RuntimeError, match="bogus-provider"):
        system_default_model_identity()
