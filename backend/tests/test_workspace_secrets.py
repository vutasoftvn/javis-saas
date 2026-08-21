import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app
from core.auth import get_current_workspace_member
from db.models import WorkspaceMember
from db.session import get_db
from core.snowflake import generate_snowflake_id
from integrations.channels.models import WorkspaceSecret
from integrations.channels.secrets_service import encrypt_for_workspace, decrypt_for_workspace


def test_encryption_decryption_per_workspace():
    ws_id = generate_snowflake_id()
    raw_key = "sk-or-v1-custom-secret-key-123"

    encrypted = encrypt_for_workspace(ws_id, raw_key)
    assert encrypted.startswith("enc:")
    assert encrypted != raw_key

    decrypted = decrypt_for_workspace(ws_id, encrypted)
    assert decrypted == raw_key


def test_encryption_isolation_between_workspaces():
    ws_1 = generate_snowflake_id()
    ws_2 = generate_snowflake_id()
    raw_key = "sk-or-v1-secret-key-xyz"

    encrypted_ws1 = encrypt_for_workspace(ws_1, raw_key)
    # Decrypting with wrong workspace_id should fail to decrypt raw key
    decrypted_wrong = decrypt_for_workspace(ws_2, encrypted_ws1)
    assert decrypted_wrong != raw_key


def test_save_and_delete_openrouter_key_endpoint():
    ws_id = generate_snowflake_id()
    mock_member = WorkspaceMember(workspace_id=ws_id, role="admin")

    db_mock = MagicMock()
    db_mock.query.return_value.filter.return_value.first.return_value = None

    app.dependency_overrides[get_current_workspace_member] = lambda: mock_member
    app.dependency_overrides[get_db] = lambda: db_mock

    try:
        client = TestClient(app)
        
        # Save key
        res = client.post(
            "/api/v1/ai/openrouter-key",
            json={"workspace_id": ws_id, "api_key": "sk-or-v1-tenant-secret-key"}
        )
        assert res.status_code == 200
        assert res.json()["is_custom_workspace_key"] is True

        # Delete key
        res_del = client.delete(f"/api/v1/ai/openrouter-key?workspace_id={ws_id}")
        assert res_del.status_code == 200
        assert res_del.json()["is_custom_workspace_key"] is False
    finally:
        app.dependency_overrides.clear()
