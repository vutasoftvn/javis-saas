from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock

from app.db.models import WorkspaceMember, WorkflowDefinition, WorkflowStep, WorkflowVersion
from app.integrations.workflows.router import list_workflow_approvals


def _self_referential_query_mock():
    """See test_platform_hub_summary.py for the same helper/rationale: a
    MagicMock DB whose fluent chain (.join/.filter/.order_by/.offset/.limit)
    always returns itself so terminal-method config applies everywhere."""
    query = MagicMock()
    query.join.return_value = query
    query.filter.return_value = query
    query.order_by.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query
    query.count.return_value = 0
    query.all.return_value = []
    return query


def test_list_workflow_approvals_scoped_by_brain_before_pagination():
    """Regression test: list_workflow_approvals used to fetch a page across ALL
    tenants first (.offset().limit()) and only discard non-matching rows
    afterwards - meaning a workspace's own pending approvals could silently
    disappear once enough other tenants' rows sorted ahead of them. The fix
    joins through WorkflowDefinition.brain_id and filters BEFORE paginating,
    the same pattern list_workflow_runs already used correctly.
    """
    ws_id = generate_snowflake_id()
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id

    db = MagicMock()
    query = _self_referential_query_mock()

    call_state = {"n": 0}

    def all_side_effect():
        call_state["n"] += 1
        if call_state["n"] == 1:
            # brain_ids lookup - give the workspace one brain.
            return [MagicMock(id=generate_snowflake_id())]
        return []

    query.all.side_effect = all_side_effect
    db.query.return_value = query

    result = list_workflow_approvals(
        workspace_id=ws_id,
        status_filter=None,
        limit=50,
        offset=0,
        member=member,
        db=db,
    )

    assert result["total"] == 0
    assert result["approvals"] == []

    join_targets = [call.args[0] for call in query.join.call_args_list if call.args]
    assert WorkflowStep in join_targets
    assert WorkflowVersion in join_targets
    assert WorkflowDefinition in join_targets, (
        "approvals must be scoped via WorkflowDefinition.brain_id before "
        "pagination, not filtered row-by-row after offset/limit."
    )


def test_list_workflow_approvals_empty_when_workspace_has_no_brains():
    """A workspace with zero brains must get an empty, honest result - not an
    unscoped query that could accidentally return other tenants' rows."""
    ws_id = generate_snowflake_id()
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id

    db = MagicMock()
    query = _self_referential_query_mock()
    query.all.return_value = []  # no brains, ever
    db.query.return_value = query

    result = list_workflow_approvals(
        workspace_id=ws_id,
        status_filter=None,
        limit=50,
        offset=0,
        member=member,
        db=db,
    )

    assert result == {"total": 0, "approvals": []}
