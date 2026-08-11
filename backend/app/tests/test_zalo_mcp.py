from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.modules.integrations import connectors_zalo_router
from app.modules.integrations.connectors_zalo_router import get_zalo_workspace_member

client = TestClient(app)


@pytest.fixture(autouse=True)
def overrides():
    member = MagicMock(user_id=101, workspace_id=202)
    app.dependency_overrides[get_zalo_workspace_member] = lambda: member
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield
    app.dependency_overrides.clear()


def _session(state="queued"):
    return MagicMock(
        id=987654321,
        state=state,
        qr_data_url=None,
        connection_id=None,
        error=None,
        expires_at=datetime.utcnow() + timedelta(minutes=3),
    )


def test_start_zalo_qr_creates_workspace_scoped_job(monkeypatch):
    created = _session()
    create = MagicMock(return_value=created)
    monkeypatch.setattr(connectors_zalo_router, "create_qr_session", create)

    response = client.post("/api/v1/connectors/zalo/sessions", json={"workspace_id": "202"})

    assert response.status_code == 202
    assert response.json()["id"] == "987654321"
    create.assert_called_once()
    assert create.call_args.args[1:] == (202, 101)


def test_zalo_qr_status_rejects_non_snowflake_id():
    response = client.get("/api/v1/connectors/zalo/sessions/not-an-id?workspace_id=202")
    assert response.status_code == 404


def test_zalo_qr_status_is_scoped_to_workspace_and_creator(monkeypatch):
    lookup = MagicMock(return_value=None)
    monkeypatch.setattr(connectors_zalo_router, "get_qr_session_for_owner", lookup)

    response = client.get("/api/v1/connectors/zalo/sessions/987654321?workspace_id=202")

    assert response.status_code == 404
    assert lookup.call_args.args[1:] == (987654321, 202, 101)


def test_cancel_zalo_qr_changes_only_owned_session(monkeypatch):
    owned = _session("qr")
    lookup = MagicMock(return_value=owned)
    cancel = MagicMock()
    monkeypatch.setattr(connectors_zalo_router, "get_qr_session_for_owner", lookup)
    monkeypatch.setattr(connectors_zalo_router, "cancel_qr_session", cancel)

    response = client.post("/api/v1/connectors/zalo/sessions/987654321/cancel?workspace_id=202")

    assert response.status_code == 200
    cancel.assert_called_once()
