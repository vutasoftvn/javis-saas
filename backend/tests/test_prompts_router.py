from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from core.auth import get_current_workspace_member
from core.protected_resources.models import ProtectedResource, ProtectedResourceRevision
from core.snowflake import generate_snowflake_id
from db.models import WorkspaceMember
from db.session import get_db
from main import app


def _override(member: WorkspaceMember, db):
    app.dependency_overrides[get_current_workspace_member] = lambda: member
    app.dependency_overrides[get_db] = lambda: db


def test_get_unknown_prompt_returns_404():
    ws_id = generate_snowflake_id()
    member = WorkspaceMember(workspace_id=ws_id, role="owner")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    _override(member, db)

    client = TestClient(app)
    res = client.get(f"/api/v1/platform/prompts/not_a_domain/not_a_name?workspace_id={ws_id}")
    assert res.status_code == 404


def test_list_prompts_requires_at_least_admin():
    ws_id = generate_snowflake_id()
    member = WorkspaceMember(workspace_id=ws_id, role="member")
    db = MagicMock()
    _override(member, db)

    client = TestClient(app)
    res = client.get(f"/api/v1/platform/prompts/?workspace_id={ws_id}")
    assert res.status_code == 403


def test_list_prompts_succeeds_for_admin_and_includes_known_wired_flag():
    ws_id = generate_snowflake_id()
    member = WorkspaceMember(workspace_id=ws_id, role="admin")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    _override(member, db)

    client = TestClient(app)
    res = client.get(f"/api/v1/platform/prompts/?workspace_id={ws_id}")
    assert res.status_code == 200
    prompts = res.json()["prompts"]
    wired = next(p for p in prompts if p["domain"] == "cosa" and p["name"] == "chat_language")
    assert wired["is_wired"] is True
    unwired = next(p for p in prompts if p["domain"] == "finance" and p["name"] == "analyze")
    assert unwired["is_wired"] is False


def test_update_prompt_blocked_for_admin_allowed_for_owner():
    ws_id = generate_snowflake_id()
    db = MagicMock()

    resource = ProtectedResource(
        id=generate_snowflake_id(), workspace_id=ws_id, resource_type="domain_prompt",
        resource_key="cosa/chat_language", active_revision_no=0, resettable=True,
    )
    rev0 = ProtectedResourceRevision(
        id=generate_snowflake_id(), resource_id=resource.id, revision_no=0,
        content_jsonb={"content": "old"}, is_default=True, status="ACTIVE",
    )
    resource_query = MagicMock()
    resource_query.filter.return_value.first.return_value = resource
    revision_query = MagicMock()
    revision_query.filter.return_value.order_by.return_value.first.return_value = rev0

    def query_mock(model):
        if model is ProtectedResource:
            return resource_query
        if model is ProtectedResourceRevision:
            return revision_query
        return MagicMock()

    db.query.side_effect = query_mock

    admin_member = WorkspaceMember(workspace_id=ws_id, user_id=generate_snowflake_id(), role="admin")
    _override(admin_member, db)
    client = TestClient(app)
    res = client.patch(
        f"/api/v1/platform/prompts/cosa/chat_language?workspace_id={ws_id}",
        json={"content": "new content from admin"},
    )
    assert res.status_code == 403

    owner_member = WorkspaceMember(workspace_id=ws_id, user_id=generate_snowflake_id(), role="owner")
    _override(owner_member, db)
    res = client.patch(
        f"/api/v1/platform/prompts/cosa/chat_language?workspace_id={ws_id}",
        json={"content": "new content from owner"},
    )
    assert res.status_code == 200
    assert res.json()["content"] == "new content from owner"


def test_reset_prompt_returns_file_default():
    ws_id = generate_snowflake_id()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.all.return_value = []

    owner_member = WorkspaceMember(workspace_id=ws_id, user_id=generate_snowflake_id(), role="owner")
    _override(owner_member, db)

    client = TestClient(app)
    res = client.post(f"/api/v1/platform/prompts/cosa/chat_language:reset?workspace_id={ws_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "reset"
