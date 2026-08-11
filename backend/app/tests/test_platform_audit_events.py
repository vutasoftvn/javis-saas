from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock

from app.db.models import WorkspaceMember
from app.modules.platform.router import list_audit_events


def _self_referential_query_mock():
    """See test_platform_hub_summary.py for the same helper/rationale."""
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query
    query.count.return_value = 0
    query.all.return_value = []
    return query


def test_list_audit_events_no_longer_falls_back_to_actor_membership():
    """Regression test for a real cross-tenant leak: list_audit_events used to
    match `metadata_jsonb.workspace_id == workspace_id OR actor_id in
    workspace_member_ids`. A user who belongs to two workspaces would leak
    their audit entries from workspace B into workspace A's audit view purely
    because they're also a member of A. The fix scopes strictly on
    metadata_jsonb.workspace_id and no longer queries WorkspaceMember at all
    for this purpose.
    """
    ws_id = generate_snowflake_id()
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id

    db = MagicMock()
    query = _self_referential_query_mock()
    db.query.return_value = query

    list_audit_events(
        workspace_id=ws_id,
        action=None,
        actor_type=None,
        limit=50,
        offset=0,
        member=member,
        db=db,
    )

    queried_targets = [call.args for call in db.query.call_args_list]
    assert not any(WorkspaceMember in args for args in queried_targets), (
        "list_audit_events must not query WorkspaceMember to build an "
        "actor-membership fallback - that was the source of the leak."
    )

    filter_args_str = " ".join(
        str(arg.compile(compile_kwargs={"literal_binds": True}))
        for call in query.filter.call_args_list
        for arg in call.args
    )
    assert "metadata_jsonb" in filter_args_str
    assert "workspace_id" in filter_args_str
    assert str(ws_id) in filter_args_str


def test_list_audit_events_valid_structure_and_real_zero():
    ws_id = generate_snowflake_id()
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id

    db = MagicMock()
    query = _self_referential_query_mock()
    db.query.return_value = query

    result = list_audit_events(
        workspace_id=ws_id,
        action=None,
        actor_type=None,
        limit=50,
        offset=0,
        member=member,
        db=db,
    )

    assert result == {"total": 0, "events": []}
