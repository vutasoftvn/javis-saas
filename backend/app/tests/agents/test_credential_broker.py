import pytest
from unittest.mock import MagicMock

from app.agents.execution.credential_broker import CredentialBroker
from app.agents.execution.errors import ExecutionErrorCode, ExecutionRuntimeError
from app.agents.execution.types import SandboxPolicy
from app.core.snowflake import generate_snowflake_id
from app.modules.integrations.models import WorkspaceSecret
from app.modules.integrations.secrets_service import encrypt_for_workspace


def test_credential_broker_blocks_unauthorized_service():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    # safe_analysis preset has empty credentials_allow
    policy = SandboxPolicy(name="safe_analysis", credentials_allow=[])

    with pytest.raises(ExecutionRuntimeError) as exc_info:
        CredentialBroker.resolve_credentials(
            db=db,
            workspace_id=ws_id,
            policy=policy,
            requested_services=["facebook"],
        )

    assert exc_info.value.code == ExecutionErrorCode.EXEC_CREDENTIAL_NOT_ALLOWED


def test_credential_broker_resolves_allowed_service():
    ws_id = generate_snowflake_id()
    policy = SandboxPolicy(name="marketing", credentials_allow=["facebook"])

    raw_token = "EAABwzL1384092fake_facebook_token"
    encrypted = encrypt_for_workspace(ws_id, raw_token)

    secret_row = WorkspaceSecret(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        key="facebook_access_token",
        encrypted_value=encrypted,
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = secret_row

    creds = CredentialBroker.resolve_credentials(
        db=db,
        workspace_id=ws_id,
        policy=policy,
        requested_services=["facebook"],
    )

    assert "FACEBOOK_ACCESS_TOKEN" in creds
    assert creds["FACEBOOK_ACCESS_TOKEN"] == raw_token


def test_credential_broker_workspace_isolation():
    ws_1 = generate_snowflake_id()
    ws_2 = generate_snowflake_id()
    policy = SandboxPolicy(name="marketing", credentials_allow=["openrouter"])

    raw_key = "sk-or-v1-secret-key-12345"
    encrypted_ws1 = encrypt_for_workspace(ws_1, raw_key)

    # If DB incorrectly queried with ws_2 for ws_1 data, decrypt_for_workspace will fail
    secret_row = WorkspaceSecret(
        id=generate_snowflake_id(),
        workspace_id=ws_1,
        key="openrouter_api_key",
        encrypted_value=encrypted_ws1,
    )

    db = MagicMock()
    # Simulated query for ws_2 returns None or secret encrypted for ws_1
    db.query.return_value.filter.return_value.first.return_value = None

    creds = CredentialBroker.resolve_credentials(
        db=db,
        workspace_id=ws_2,
        policy=policy,
        requested_services=["openrouter"],
    )

    assert creds == {}
