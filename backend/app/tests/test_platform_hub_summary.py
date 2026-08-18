from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.db.models import WorkspaceMember, WorkflowDefinition, WorkflowStep
from app.platform.core.router import get_hub_summary
from app.platform.core.hub_service import get_hub_summary_data


def test_hub_summary_cross_tenant_forbidden():
    """Verify that a member from workspace A cannot access hub-summary of workspace B."""
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = generate_snowflake_id()

    other_workspace_id = generate_snowflake_id()
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        get_hub_summary(workspace_id=other_workspace_id, member=member, db=db)

    assert exc_info.value.status_code == 403
    assert "Access forbidden" in exc_info.value.detail


def _self_referential_query_mock():
    """A MagicMock DB whose fluent query chain (.join/.filter/.order_by/.limit)
    always returns itself, so any call site's chain collapses to the same object
    regardless of depth - lets a single terminal-method config apply everywhere.
    """
    query = MagicMock()
    query.join.return_value = query
    query.outerjoin.return_value = query
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.scalar.return_value = 0
    query.all.return_value = []
    return query


def test_hub_summary_valid_structure_and_real_zero():
    """A brand-new/empty workspace must see real zeros and empty lists - never
    the previous hardcoded demo numbers (18 projects, 152 tasks, 7 dev jobs...)."""
    ws_id = generate_snowflake_id()
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id

    db = MagicMock()
    query = _self_referential_query_mock()

    # The very first `.all()` call in get_hub_summary_data is the brain_ids
    # lookup (`db.query(Brain.id).filter(...).all()`); give it one brain so the
    # brain-scoped branches (workflows, vault, chat) actually execute, then make
    # every subsequent `.all()` call return empty (no agents/tasks/chats).
    call_state = {"n": 0}

    def all_side_effect():
        call_state["n"] += 1
        if call_state["n"] == 1:
            return [MagicMock(id=generate_snowflake_id())]
        return []

    query.all.side_effect = all_side_effect
    db.query.return_value = query

    summary = get_hub_summary_data(db=db, workspace_id=ws_id)

    assert summary["status"] == "active"
    assert "system_health" in summary
    assert summary["system_health"]["status"] == "OPTIMAL"
    assert "sync_integrity" not in summary["system_health"]
    assert "voice_engine" in summary
    assert "subsystems" in summary
    assert summary["subsystems"]["active_count"] == 7
    assert len(summary["subsystems"]["items"]) == 7
    assert "memory_core" in summary
    assert "active_agents" in summary
    assert "build_mode" in summary
    assert summary["build_mode"]["available"] is False
    assert "kpi_strip" in summary
    for key in ("projects", "tasks", "okrs", "workflows", "knowledge", "automations"):
        assert summary["kpi_strip"][key]["count"] == 0, f"{key} should be a real zero, not a demo fallback"
    assert summary["kpi_strip"]["dev_jobs"]["count"] == 0
    assert summary["kpi_strip"]["dev_jobs"]["is_dev_preview"] is True
    assert summary["active_agents"]["items"] == []
    assert summary["recent_activity"] == []


def test_hub_summary_workflow_counts_are_brain_scoped_not_task_null_leak():
    """Regression test for two cross-tenant leaks that used to exist:
    (1) `active_workflow_runs` counted every tenant's task-unlinked runs via
        `outerjoin(Task...).filter(or_(..., WorkflowRun.task_id.is_(None)))`.
    (2) `pending_workflow_approvals` counted ALL tenants' pending approvals with
        zero workspace/brain scoping at all.
    Both must now go through the same WorkflowDefinition.brain_id-scoped join
    chain that workflows/router.py::list_workflow_runs uses. This test proves
    the fix's shape rather than asserting on unstable literal counts.
    """
    ws_id = generate_snowflake_id()
    db = MagicMock()
    query = _self_referential_query_mock()

    call_state = {"n": 0}

    def all_side_effect():
        call_state["n"] += 1
        if call_state["n"] == 1:
            return [MagicMock(id=generate_snowflake_id())]
        return []

    query.all.side_effect = all_side_effect
    db.query.return_value = query

    get_hub_summary_data(db=db, workspace_id=ws_id)

    # The leaky `outerjoin` pattern must be gone entirely.
    assert not query.outerjoin.called, (
        "active_workflow_runs must not use outerjoin(Task...) with an "
        "unscoped task_id.is_(None) branch - that was the cross-tenant leak."
    )

    join_targets = [call.args[0] for call in query.join.call_args_list if call.args]
    assert WorkflowDefinition in join_targets, (
        "workflow run/approval counts must join through WorkflowDefinition "
        "(brain-scoped), the same derivation list_workflow_runs uses."
    )
    assert WorkflowStep in join_targets, (
        "pending_workflow_approvals must join through WorkflowStep to reach "
        "WorkflowRun -> WorkflowDefinition; it previously had zero scoping."
    )
