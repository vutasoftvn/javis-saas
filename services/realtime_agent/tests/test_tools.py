import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import (  # noqa: E402
    NAVIGATION_TARGETS,
    _approve_action_impl,
    _get_ceo_brief_impl,
    _get_developer_job_status_impl,
    _get_next_best_actions_impl,
    _get_pending_approvals_impl,
    _get_portfolio_status_impl,
    _get_project_status_impl,
    _open_navigation_impl,
    _reject_action_impl,
    _request_developer_job_impl,
    _runtime_create_handoff_impl,
    _runtime_get_blockers_impl,
    _runtime_get_checkpoint_status_impl,
    _runtime_get_dag_impl,
    _runtime_get_needs_you_impl,
    _runtime_get_status_impl,
    _runtime_resolve_blocker_impl,
    _work_get_inspector_impl,
    _work_review_impl,
    _work_rework_impl,
)


def test_get_ceo_brief_impl_delegates_to_backend_tools():
    with patch("tools.backend_tools.get_ceo_brief") as mock_brief, patch("tools.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_brief.return_value = {"status": "active"}

        result = _get_ceo_brief_impl(workspace_id=123)

    mock_brief.assert_called_once_with(mock_db, 123)
    mock_db.close.assert_called_once()
    assert result == {"status": "active"}


def test_get_next_best_actions_impl_delegates_to_backend_tools():
    with patch("tools.backend_tools.get_next_best_actions") as mock_nba, patch(
        "tools.SessionLocal"
    ) as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_nba.return_value = {"enabled": True, "next_actions": []}

        result = _get_next_best_actions_impl(workspace_id=123, user_id=456, limit=3)

    mock_nba.assert_called_once_with(mock_db, 123, 456, 3)
    assert result == {"enabled": True, "next_actions": []}


def test_get_project_status_impl_delegates_to_backend_tools():
    with patch("tools.backend_tools.get_project_status") as mock_status, patch(
        "tools.SessionLocal"
    ) as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_status.return_value = {"found": True, "title": "mVault"}

        result = _get_project_status_impl(workspace_id=123, project_id=789)

    mock_status.assert_called_once_with(mock_db, 123, 789)
    mock_db.close.assert_called_once()
    assert result == {"found": True, "title": "mVault"}


def test_get_portfolio_status_impl_delegates_to_backend_tools():
    with patch("tools.backend_tools.get_portfolio_status") as mock_status, patch(
        "tools.SessionLocal"
    ) as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_status.return_value = {"enabled": True, "found": True, "portfolio": {}}

        result = _get_portfolio_status_impl(workspace_id=123, user_id=456, portfolio_id=999)

    mock_status.assert_called_once_with(mock_db, 123, 456, 999)
    mock_db.close.assert_called_once()
    assert result == {"enabled": True, "found": True, "portfolio": {}}


def test_get_developer_job_status_impl_delegates_to_backend_tools():
    with patch("tools.backend_tools.get_developer_job_status") as mock_status, patch(
        "tools.SessionLocal"
    ) as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_status.return_value = {"found": True, "status": "RUNNING"}

        result = _get_developer_job_status_impl(workspace_id=123, job_id=555)

    mock_status.assert_called_once_with(mock_db, 123, 555)
    mock_db.close.assert_called_once()
    assert result == {"found": True, "status": "RUNNING"}


def test_request_developer_job_impl_delegates_to_backend_tools_with_voice_command_id():
    with patch("tools.backend_tools.request_developer_job") as mock_request, patch(
        "tools.SessionLocal"
    ) as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_request.return_value = {"job_id": "999", "status": "QUEUED"}

        result = _request_developer_job_impl(
            workspace_id=123, user_id=456, title="Implement X", voice_command_id="call_abc123"
        )

    mock_request.assert_called_once_with(mock_db, 123, 456, "Implement X", "call_abc123")
    assert result == {"job_id": "999", "status": "QUEUED"}


def test_get_pending_approvals_impl_delegates_to_backend_tools():
    with patch("tools.backend_tools.get_pending_approvals") as mock_approvals, patch(
        "tools.SessionLocal"
    ) as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_approvals.return_value = {"total": 0, "approvals": []}

        result = _get_pending_approvals_impl(workspace_id=123, limit=3)

    mock_approvals.assert_called_once_with(mock_db, 123, 3)
    assert result == {"total": 0, "approvals": []}


def test_approve_action_impl_delegates_to_backend_tools():
    with patch("tools.backend_tools.approve_action") as mock_approve, patch(
        "tools.SessionLocal"
    ) as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_approve.return_value = {"status": "success"}

        result = _approve_action_impl(workspace_id=123, user_id=456, step_id=777)

    mock_approve.assert_called_once_with(mock_db, 123, 456, 777)
    assert result == {"status": "success"}


def test_reject_action_impl_delegates_to_backend_tools():
    with patch("tools.backend_tools.reject_action") as mock_reject, patch(
        "tools.SessionLocal"
    ) as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_reject.return_value = {"status": "success"}

        result = _reject_action_impl(workspace_id=123, user_id=456, step_id=777)

    mock_reject.assert_called_once_with(mock_db, 123, 456, 777)
    assert result == {"status": "success"}


def test_open_navigation_rejects_target_outside_whitelist():
    """The most important test in this module - the guard against the voice
    model fabricating a navigation route (spec §57)."""
    publish = MagicMock()

    result = _open_navigation_impl(publish, "delete_everything", None)

    assert result == {
        "ok": False,
        "error": f"target không hợp lệ, chỉ chấp nhận: {sorted(NAVIGATION_TARGETS)}",
    }
    publish.assert_not_called()


def test_open_navigation_accepts_whitelisted_target():
    publish = MagicMock()

    result = _open_navigation_impl(publish, "tasks", "mVault")

    assert result == {"ok": True}
    publish.assert_called_once_with("tasks", "mVault")


# --- V13.1 Company Runtime -------------------------------------------------


def test_navigation_whitelist_covers_company_runtime_screens():
    """These three must stay in the whitelist or the matching cases in
    HologramHubController::handleVoiceNavigation become unreachable - the
    controller falls back to the dashboard for any target rejected here."""
    assert {"needs_you", "blocked_work", "work_inspector"} <= NAVIGATION_TARGETS


def _assert_delegates(impl, backend_name, call_kwargs, expected_args):
    """Every runtime impl must open a session, delegate to the backend tool
    with the session as first arg, and close the session."""
    with patch(f"tools.runtime_tools.{backend_name}") as mock_tool, patch("tools.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_tool.return_value = {"ok": True}

        result = impl(**call_kwargs)

    mock_tool.assert_called_once_with(mock_db, *expected_args)
    mock_db.close.assert_called_once()
    assert result == {"ok": True}


def test_runtime_get_status_impl_delegates():
    _assert_delegates(_runtime_get_status_impl, "runtime_get_status", {"workspace_id": 123}, (123,))


def test_runtime_get_dag_impl_delegates():
    _assert_delegates(_runtime_get_dag_impl, "runtime_get_dag", {"workspace_id": 123}, (123,))


def test_runtime_get_blockers_impl_delegates():
    _assert_delegates(_runtime_get_blockers_impl, "runtime_get_blockers", {"workspace_id": 123}, (123,))


def test_runtime_resolve_blocker_impl_delegates():
    _assert_delegates(
        _runtime_resolve_blocker_impl,
        "runtime_resolve_blocker",
        {"workspace_id": 123, "blocker_id": 99},
        (123, 99),
    )


def test_runtime_get_needs_you_impl_delegates():
    _assert_delegates(_runtime_get_needs_you_impl, "runtime_get_needs_you", {"workspace_id": 123}, (123,))


def test_runtime_create_handoff_impl_delegates():
    _assert_delegates(
        _runtime_create_handoff_impl,
        "runtime_create_handoff",
        {
            "workspace_id": 123,
            "from_function": "MARKETING",
            "to_function": "TECH",
            "handoff_type": "REQUEST",
            "requested_action": "ship landing page",
        },
        (123, "MARKETING", "TECH", "REQUEST", "ship landing page"),
    )


def test_work_review_impl_passes_user_id_as_reviewer():
    _assert_delegates(
        _work_review_impl,
        "work_review",
        {"workspace_id": 123, "user_id": 456, "outcome_id": 77, "result": "ACCEPTED", "feedback": None},
        (123, 77, "ACCEPTED", None, 456),
    )


def test_work_rework_impl_passes_user_id_as_reviewer():
    _assert_delegates(
        _work_rework_impl,
        "work_rework",
        {"workspace_id": 123, "user_id": 456, "outcome_id": 77, "feedback": "thiếu số liệu"},
        (123, 77, "thiếu số liệu", 456),
    )


def test_work_get_inspector_impl_delegates():
    _assert_delegates(_work_get_inspector_impl, "work_get_inspector", {"workspace_id": 123, "task_id": 55}, (123, 55))


def test_runtime_get_checkpoint_status_impl_delegates():
    _assert_delegates(
        _runtime_get_checkpoint_status_impl, "runtime_get_checkpoint_status", {"workspace_id": 123}, (123,)
    )


# Registered in tool_registry for internal/HTTP callers, deliberately given no
# voice wrapper. Anything added here is unreachable by voice by design.
REGISTRY_ONLY_TOOLS = {"runtime.classify_intent"}


def test_every_registered_tool_has_a_voice_wrapper():
    """Guards the silent-drift failure mode: a tool can be registered in
    tool_registry and pass every backend test while having no wrapper in
    build_tools, which makes it uncallable by voice. build_tools filters its
    wrapper dict by qualified name, so a missing *or* misspelled key simply
    disappears instead of raising."""
    import tools as tools_module
    from app.core.tool_registry import get_registered_tools

    specs = get_registered_tools()
    with patch("tools.available_tools", return_value=list(specs.values())), patch("tools.SessionLocal"):
        built = tools_module.build_tools(room=MagicMock(), workspace_id=1, user_id=2)

    # +1 for open_navigation, which is always appended outside the flag filter.
    expected = len(specs) - len(REGISTRY_ONLY_TOOLS) + 1
    assert len(built) == expected, (
        f"expected {expected} voice tools, got {len(built)} - a registered tool is "
        f"missing its wrapper in build_tools, or a wrapper key is misspelled"
    )


def test_company_runtime_voice_tools_are_exposed():
    """The spec's headline voice commands must actually resolve."""
    import tools as tools_module
    from app.core.tool_registry import get_registered_tools

    specs = get_registered_tools()
    with patch("tools.available_tools", return_value=list(specs.values())), patch("tools.SessionLocal"):
        built = tools_module.build_tools(room=MagicMock(), workspace_id=1, user_id=2)

    names = {t.info.name for t in built}
    assert {"get_blockers", "get_needs_you", "get_dependency_graph", "get_runtime_status"} <= names


def test_disabled_flag_removes_company_runtime_tools():
    """With the V13.1 flags off, none of the runtime tools reach the model."""
    import tools as tools_module
    from app.core.tool_registry import get_registered_tools

    non_runtime = [
        spec
        for name, spec in get_registered_tools().items()
        if not name.startswith("runtime.") and not name.startswith("work.")
    ]
    with patch("tools.available_tools", return_value=non_runtime), patch("tools.SessionLocal"):
        built = tools_module.build_tools(room=MagicMock(), workspace_id=1, user_id=2)

    names = {t.info.name for t in built}
    assert "get_blockers" not in names
    assert "get_needs_you" not in names
    assert "get_ceo_brief" in names
