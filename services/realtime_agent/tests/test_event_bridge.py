import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from event_bridge import (  # noqa: E402
    RealtimeEvent,
    mark_session_active,
    mark_session_error,
    publish_hologram_state,
    publish_ui_command,
)


def test_publish_hologram_state_sends_expected_payload():
    room = MagicMock()

    publish_hologram_state(room, "LISTENING")

    room.local_participant.publish_data.assert_called_once()
    payload, kwargs = room.local_participant.publish_data.call_args
    assert b'"type": "HOLOGRAM_STATE"' in payload[0]
    assert b'"state": "LISTENING"' in payload[0]
    assert kwargs == {"reliable": True, "topic": "hologram"}


def test_publish_ui_command_sends_expected_payload():
    room = MagicMock()

    publish_ui_command(room, "tasks", "mVault")

    room.local_participant.publish_data.assert_called_once()
    payload, kwargs = room.local_participant.publish_data.call_args
    assert b'"type": "UI_COMMAND"' in payload[0]
    assert b'"command": "OPEN_ROUTE"' in payload[0]
    assert b'"target": "tasks"' in payload[0]
    assert kwargs == {"reliable": True, "topic": "hologram"}


def test_mark_session_active_sets_status_and_started_at():
    with patch("event_bridge.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_session = MagicMock(status="creating", id=42)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        mark_session_active("cosa-1-2-3")

    assert mock_session.status == "active"
    assert mock_session.started_at is not None
    mock_db.commit.assert_called_once()
    mock_db.close.assert_called_once()

    added_event = mock_db.add.call_args[0][0]
    assert isinstance(added_event, RealtimeEvent)
    assert added_event.session_id == 42
    assert added_event.event_type == "SESSION_CONNECTED"


def test_mark_session_active_noop_when_session_missing():
    with patch("event_bridge.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mark_session_active("cosa-1-2-3")

    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()
    mock_db.close.assert_called_once()


def test_mark_session_active_does_not_resurrect_ended_session():
    with patch("event_bridge.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_session = MagicMock(status="ended")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        mark_session_active("cosa-1-2-3")

    assert mock_session.status == "ended"
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()


def test_mark_session_error_sets_status():
    with patch("event_bridge.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_session = MagicMock(status="active", id=42)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        mark_session_error("cosa-1-2-3")

    assert mock_session.status == "error"
    mock_db.commit.assert_called_once()

    added_event = mock_db.add.call_args[0][0]
    assert isinstance(added_event, RealtimeEvent)
    assert added_event.session_id == 42
    assert added_event.event_type == "SESSION_ERROR"


def test_mark_session_error_does_not_override_ended_session():
    with patch("event_bridge.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_session = MagicMock(status="ended")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        mark_session_error("cosa-1-2-3")

    assert mock_session.status == "ended"
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()
