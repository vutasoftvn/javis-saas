import uuid
from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock

import pytest

from app.db.models import MCPConnection
from app.modules.integrations import google_connection_service as service
from app.modules.integrations.google_connection_service import GoogleNotConnected


@pytest.fixture(autouse=True)
def _master_key(monkeypatch):
    monkeypatch.setenv("MASTER_SECRET_KEY", "test-master-key")


def _db_with(connections):
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = connections
    return db


def _connection(config):
    return MCPConnection(
        id=generate_snowflake_id(),
        workspace_id=generate_snowflake_id(),
        name="Google Workspace",
        status="connected",
        config_jsonb=config,
    )


def test_a_connection_without_a_token_is_not_usable():
    """Chính xác là bản ghi mà luồng "kết nối" giả sinh ra: có dòng trong DB, status
    'connected', nhưng không có gì để gọi Gmail. Coi nó là đã kết nối là lừa người dùng."""
    db = _db_with([_connection({"type": "google_workspace", "email": "a@b.com"})])

    assert service.has_usable_google_connection(db, generate_snowflake_id()) is False


def test_a_connection_with_a_refresh_token_is_usable():
    db = _db_with(
        [_connection({"type": "google_workspace", "email": "a@b.com", "refresh_token": "enc:x"})]
    )

    assert service.has_usable_google_connection(db, generate_snowflake_id()) is True


def test_other_connectors_are_ignored():
    db = _db_with([_connection({"type": "zalo_personal", "refresh_token": "enc:x"})])

    assert service.get_google_connection(db, generate_snowflake_id()) is None
    assert service.has_usable_google_connection(db, generate_snowflake_id()) is False


def test_refresh_token_is_stored_encrypted_not_in_the_clear():
    """config_jsonb đọc được bằng một câu SELECT; refresh token nằm đó ở dạng chữ thường là
    ai xem được DB cũng đọc trọn hòm thư người dùng."""
    workspace_id = generate_snowflake_id()
    db = _db_with([])

    service.store_connection(db, workspace_id, "a@b.com", "1//refresh-token-that")

    stored = db.add.call_args[0][0]
    assert stored.config_jsonb["refresh_token"].startswith("enc:")
    assert "1//refresh-token-that" not in stored.config_jsonb["refresh_token"]


def test_stored_token_can_be_read_back_for_the_same_workspace():
    workspace_id = generate_snowflake_id()
    db = _db_with([])
    service.store_connection(db, workspace_id, "a@b.com", "1//refresh-token-that")
    stored = db.add.call_args[0][0]

    assert service.get_refresh_token(_db_with([stored]), workspace_id) == "1//refresh-token-that"


def test_a_token_from_another_workspace_cannot_be_decrypted():
    """Khoá mã hoá dẫn xuất theo workspace_id - đọc nhầm workspace thì ra rỗng chứ không
    ra token của người khác."""
    db = _db_with([])
    service.store_connection(db, generate_snowflake_id(), "a@b.com", "1//refresh-token-that")
    stored = db.add.call_args[0][0]

    with pytest.raises(GoogleNotConnected):
        service.get_refresh_token(_db_with([stored]), generate_snowflake_id())


def test_legacy_record_tells_the_user_to_reconnect():
    db = _db_with([_connection({"type": "google_workspace", "email": "a@b.com"})])

    with pytest.raises(GoogleNotConnected) as exc:
        service.get_refresh_token(db, generate_snowflake_id())

    assert "kết nối lại" in str(exc.value)
