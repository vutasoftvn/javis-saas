import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from core.authz import authorize, PROTECTED_ACTIONS
from core.snowflake import generate_snowflake_id
from db.models import WorkspaceMember, Agent
from core.protected_resources import service as protected_resource_service
from core.protected_resources.models import ProtectedResource, ProtectedResourceRevision
from platform_core.core.models import AuditLog


def test_authz_allows_admin_and_owner_for_admin_level_actions():
    admin_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=generate_snowflake_id(), user_id=generate_snowflake_id(), role="admin")
    owner_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=generate_snowflake_id(), user_id=generate_snowflake_id(), role="owner")

    for action in ["prompt.read", "spec.update", "spec.reset", "skill.update"]:
        authorize(admin_member, action)
        authorize(owner_member, action)


def test_authz_prompt_update_and_reset_require_owner():
    admin_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=generate_snowflake_id(), user_id=generate_snowflake_id(), role="admin")
    owner_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=generate_snowflake_id(), user_id=generate_snowflake_id(), role="owner")

    for action in ["prompt.update", "prompt.reset"]:
        with pytest.raises(HTTPException) as exc_info:
            authorize(admin_member, action)
        assert exc_info.value.status_code == 403

        authorize(owner_member, action)


def test_authz_blocks_non_admin():
    for role in ["member", "viewer", "editor"]:
        member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=generate_snowflake_id(), user_id=generate_snowflake_id(), role=role)
        for action in ["prompt.update", "prompt.reset", "spec.update", "spec.reset"]:
            with pytest.raises(HTTPException) as exc_info:
                authorize(member, action)
            assert exc_info.value.status_code == 403


def test_protected_resources_lifecycle():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    # 1. get_or_create_resource when not existing
    db.query.return_value.filter.return_value.first.return_value = None
    resource = protected_resource_service.get_or_create_resource(
        db=db,
        workspace_id=ws_id,
        resource_type="agent_prompt",
        resource_key="agent:1:system_prompt",
        default_content={"system_prompt": "default prompt"},
    )
    assert resource.workspace_id == ws_id
    assert resource.active_revision_no == 0

    # 2. create_revision
    db.query.return_value.filter.return_value.first.return_value = resource
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = ProtectedResourceRevision(
        id=generate_snowflake_id(), resource_id=resource.id, revision_no=0, content_jsonb={}, is_default=True, status="ACTIVE"
    )

    rev1 = protected_resource_service.create_revision(
        db=db,
        workspace_id=ws_id,
        resource_type="agent_prompt",
        resource_key="agent:1:system_prompt",
        content={"system_prompt": "custom prompt v1"},
        actor_id=user_id,
    )
    assert rev1.revision_no == 1
    assert resource.active_revision_no == 1
    assert rev1.content_jsonb["system_prompt"] == "custom prompt v1"

    # Verify AuditLog was added
    added_objects = [call.args[0] for call in db.add.call_args_list]
    audit_logs = [obj for obj in added_objects if isinstance(obj, AuditLog)]
    assert len(audit_logs) > 0
    assert audit_logs[-1].action in ("CREATE_OVERRIDE", "UPDATE")

    # 3. reset_to_default
    db.query.return_value.filter.return_value.first.return_value = resource
    overrides = [rev1]
    db.query.return_value.filter.return_value.all.return_value = overrides

    reset_success = protected_resource_service.reset_to_default(
        db=db,
        workspace_id=ws_id,
        resource_type="agent_prompt",
        resource_key="agent:1:system_prompt",
        actor_id=user_id,
    )
    assert reset_success is True
    assert resource.active_revision_no == 0
    assert rev1.status == "ARCHIVED"


def test_agents_router_prompt_update_rbac():
    from founder_os.tasks.agents_router import update_agent, AgentUpdate

    db = MagicMock()
    ws_id = generate_snowflake_id()
    agent_id = generate_snowflake_id()
    agent = Agent(id=agent_id, workspace_id=ws_id, name="Test Agent", slug="test", system_prompt="old prompt")
    resource = ProtectedResource(id=generate_snowflake_id(), workspace_id=ws_id, resource_type="agent_prompt", resource_key=f"agent:{agent_id}:system_prompt", active_revision_no=0, resettable=True)
    rev0 = ProtectedResourceRevision(id=generate_snowflake_id(), resource_id=resource.id, revision_no=0, content_jsonb={"system_prompt": "old prompt"}, is_default=True, status="ACTIVE")

    agent_query = MagicMock()
    agent_query.filter.return_value.first.return_value = agent

    res_query = MagicMock()
    res_query.filter.return_value.first.return_value = resource

    rev_query = MagicMock()
    rev_query.filter.return_value.order_by.return_value.first.return_value = rev0
    rev_query.filter.return_value.first.return_value = rev0

    def query_mock(model):
        if model == Agent:
            return agent_query
        elif model == ProtectedResource:
            return res_query
        elif model == ProtectedResourceRevision:
            return rev_query
        return MagicMock()

    db.query.side_effect = query_mock

    # Member role should be blocked from updating system_prompt
    regular_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=ws_id, user_id=generate_snowflake_id(), role="member")
    with pytest.raises(HTTPException) as exc:
        update_agent(
            workspace_id=ws_id,
            agent_id=agent_id,
            agent_in=AgentUpdate(system_prompt="new prompt"),
            member=regular_member,
            db=db,
        )
    assert exc.value.status_code == 403

    # Admin role is no longer sufficient for prompt.update (owner-only as of this change)
    admin_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=ws_id, user_id=generate_snowflake_id(), role="admin")
    with pytest.raises(HTTPException) as exc:
        update_agent(
            workspace_id=ws_id,
            agent_id=agent_id,
            agent_in=AgentUpdate(system_prompt="new prompt from admin"),
            member=admin_member,
            db=db,
        )
    assert exc.value.status_code == 403

    # Owner role succeeds
    owner_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=ws_id, user_id=generate_snowflake_id(), role="owner")
    res = update_agent(
        workspace_id=ws_id,
        agent_id=agent_id,
        agent_in=AgentUpdate(system_prompt="new prompt from owner"),
        member=owner_member,
        db=db,
    )
    assert res["system_prompt"] == "new prompt from owner"


def test_agents_router_reset_and_revisions_endpoints():
    from founder_os.tasks.agents_router import reset_agent_system_prompt, list_agent_prompt_revisions

    db = MagicMock()
    ws_id = generate_snowflake_id()
    agent_id = generate_snowflake_id()
    agent = Agent(id=agent_id, workspace_id=ws_id, name="Test Agent", slug="test", system_prompt="custom prompt")
    resource = ProtectedResource(id=generate_snowflake_id(), workspace_id=ws_id, resource_type="agent_prompt", resource_key=f"agent:{agent_id}:system_prompt", active_revision_no=1, resettable=True)
    rev0 = ProtectedResourceRevision(id=generate_snowflake_id(), resource_id=resource.id, revision_no=0, content_jsonb={"system_prompt": "default prompt"}, is_default=True, status="ACTIVE")

    agent_query = MagicMock()
    agent_query.filter.return_value.first.return_value = agent

    res_query = MagicMock()
    res_query.filter.return_value.first.return_value = resource

    rev_query = MagicMock()
    rev_query.filter.return_value.all.return_value = []
    rev_query.filter.return_value.order_by.return_value.all.return_value = [rev0]
    rev_query.filter.return_value.first.return_value = rev0

    def query_mock(model):
        if model == Agent:
            return agent_query
        elif model == ProtectedResource:
            return res_query
        elif model == ProtectedResourceRevision:
            return rev_query
        return MagicMock()

    db.query.side_effect = query_mock

    regular_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=ws_id, user_id=generate_snowflake_id(), role="member")
    admin_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=ws_id, user_id=generate_snowflake_id(), role="admin")
    owner_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=ws_id, user_id=generate_snowflake_id(), role="owner")

    # Non-admin reset -> 403
    with pytest.raises(HTTPException) as exc:
        reset_agent_system_prompt(workspace_id=ws_id, agent_id=agent_id, member=regular_member, db=db)
    assert exc.value.status_code == 403

    # Admin reset -> also 403 now (reset requires owner)
    with pytest.raises(HTTPException) as exc:
        reset_agent_system_prompt(workspace_id=ws_id, agent_id=agent_id, member=admin_member, db=db)
    assert exc.value.status_code == 403

    # Owner reset -> succeeds
    reset_res = reset_agent_system_prompt(workspace_id=ws_id, agent_id=agent_id, member=owner_member, db=db)
    assert reset_res["status"] == "reset"

    # Non-admin list revisions -> 403
    with pytest.raises(HTTPException) as exc:
        list_agent_prompt_revisions(workspace_id=ws_id, agent_id=agent_id, member=regular_member, db=db)
    assert exc.value.status_code == 403

    # Admin list revisions -> still succeeds (prompt.read stays admin-level)
    revisions_res = list_agent_prompt_revisions(workspace_id=ws_id, agent_id=agent_id, member=admin_member, db=db)
    assert "revisions" in revisions_res

