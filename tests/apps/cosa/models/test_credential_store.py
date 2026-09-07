"""Task 2 (plan 2026-09-07-local-first-model-routing) — `LocalCredentialStore`:
mã hoá AES-256-GCM tại chỗ, workspace-scoped (AAD = workspace_id, cross-
workspace decrypt fail-closed), key cục bộ đọc từ `COSA_LOCAL_SECRETS_KEY_FILE`
(reject key file thiếu/group-world-readable/không tuyệt đối ở production)."""

from __future__ import annotations

import base64
import os
import stat

import pytest
from pydantic import SecretStr

from apps.cosa.models.credential_store import (
    CredentialNotFound,
    CredentialReference,
    CredentialStoreError,
    InMemoryCredentialRepository,
    LocalCredentialStore,
    load_local_secrets_key,
)


@pytest.fixture
def key_file(tmp_path) -> str:
    path = tmp_path / "local_secrets.key"
    key = os.urandom(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(base64.b64encode(key).decode())
    return str(path)


@pytest.fixture
def store(key_file: str) -> LocalCredentialStore:
    return LocalCredentialStore(InMemoryCredentialRepository(), key_file_path=key_file)


@pytest.mark.asyncio
async def test_ciphertext_has_no_plaintext_and_is_workspace_scoped(
    store: LocalCredentialStore,
) -> None:
    ref = await store.put("ws-a", SecretStr("sk-secret"))

    raw = await store.raw_ciphertext_for_test(ref.id)
    assert "sk-secret" not in raw

    with pytest.raises(CredentialNotFound):
        await store.get("ws-b", ref.id)


@pytest.mark.asyncio
async def test_correct_workspace_can_decrypt(store: LocalCredentialStore) -> None:
    ref = await store.put("ws-a", SecretStr("sk-secret"))

    secret = await store.get("ws-a", ref.id)

    assert secret.get_secret_value() == "sk-secret"


@pytest.mark.asyncio
async def test_missing_credential_id_raises_not_found(store: LocalCredentialStore) -> None:
    with pytest.raises(CredentialNotFound):
        await store.get("ws-a", "cred-does-not-exist")


@pytest.mark.asyncio
async def test_credential_reference_never_carries_plaintext(store: LocalCredentialStore) -> None:
    ref = await store.put("ws-a", SecretStr("sk-secret"))

    assert "sk-secret" not in repr(ref)
    assert "sk-secret" not in str(ref)
    assert "sk-secret" not in ref.model_dump_json()
    with pytest.raises(ValueError):
        CredentialReference(
            id=ref.id, workspace_id="ws-a", key_version=1, api_key="sk-should-not-exist"
        )


@pytest.mark.asyncio
async def test_key_file_missing_in_dev_is_auto_created_0600(tmp_path) -> None:
    path = tmp_path / "nested" / "local_secrets.key"
    key = load_local_secrets_key(str(path))

    assert len(key) == 32
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600


def test_key_file_group_readable_is_rejected(tmp_path) -> None:
    path = tmp_path / "local_secrets.key"
    path.write_text(base64.b64encode(os.urandom(32)).decode())
    os.chmod(path, 0o640)

    with pytest.raises(CredentialStoreError):
        load_local_secrets_key(str(path))


def test_key_file_world_readable_is_rejected(tmp_path) -> None:
    path = tmp_path / "local_secrets.key"
    path.write_text(base64.b64encode(os.urandom(32)).decode())
    os.chmod(path, 0o644)

    with pytest.raises(CredentialStoreError):
        load_local_secrets_key(str(path))


def test_missing_key_file_in_production_is_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    missing_path = tmp_path / "does-not-exist.key"

    with pytest.raises(CredentialStoreError):
        load_local_secrets_key(str(missing_path))


def test_relative_key_file_path_rejected_in_production(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(CredentialStoreError):
        load_local_secrets_key("relative/path/secrets.key")


def test_no_key_file_configured_in_production_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("COSA_LOCAL_SECRETS_KEY_FILE", raising=False)

    with pytest.raises(CredentialStoreError):
        load_local_secrets_key(None)


@pytest.mark.asyncio
async def test_wrong_workspace_decrypt_failure_does_not_leak_plaintext_in_exception(
    store: LocalCredentialStore,
) -> None:
    ref = await store.put("ws-a", SecretStr("sk-super-secret-value"))

    with pytest.raises(CredentialNotFound) as exc_info:
        await store.get("ws-b", ref.id)

    assert "sk-super-secret-value" not in str(exc_info.value)
