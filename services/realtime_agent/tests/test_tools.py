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
