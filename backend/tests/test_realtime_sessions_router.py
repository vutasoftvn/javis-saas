from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from datetime import datetime

from core.snowflake import generate_snowflake_id
from integrations.realtime.models import RealtimeSession, VoiceUsageRecord
from integrations.realtime.router import (
    RealtimeSessionCreateRequest,
    RealtimeSessionEndRequest,
    create_realtime_session,
    end_realtime_session,
    realtime_health,
)


def _member(workspace_id, user_id=None):
    m = MagicMock()
    m.workspace_id = workspace_id
    m.user_id = user_id or generate_snowflake_id()
    return m


def test_create_session_cross_tenant_forbidden():
    """A member of workspace A must not be able to open a realtime session
    scoped to workspace B just by passing B's id in the query string. This is
    a defense-in-depth check inside the handler itself (matching
    platform/router.py's pattern), not just reliance on FastAPI's name-based
    Depends binding of get_current_workspace_member."""
    member = _member(workspace_id=generate_snowflake_id())
    other_workspace_id = generate_snowflake_id()
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        create_realtime_session(
            workspace_id=other_workspace_id,
            data=RealtimeSessionCreateRequest(device_type="desktop"),
            member=member,
            db=db,
        )

    assert exc_info.value.status_code == 403


@patch("integrations.realtime.router.generate_livekit_token")
@patch("integrations.realtime.router.is_enabled", return_value=False)
def test_create_session_success_returns_token_and_room(mock_is_enabled, mock_token):
    mock_token.return_value = "fake.jwt.token"
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    member = _member(workspace_id=ws_id, user_id=user_id)
    db = MagicMock()

    with patch.dict("os.environ", {"LIVEKIT_URL": "wss://example.livekit.cloud"}):
        result = create_realtime_session(
            workspace_id=ws_id,
            data=RealtimeSessionCreateRequest(device_type="desktop"),
            member=member,
            db=db,
        )

    assert result["token"] == "fake.jwt.token"
    assert result["livekit_url"] == "wss://example.livekit.cloud"
    assert result["room_name"].startswith(f"cosa-{ws_id}-{user_id}-")
    assert result["status"] == "creating"
    assert db.add.called
    assert db.commit.called


@patch("integrations.realtime.router.generate_livekit_token", return_value="fake.jwt.token")
@patch("integrations.realtime.router.is_enabled", return_value=False)
def test_create_session_defaults_to_cloud_transport_when_flag_off(mock_is_enabled, mock_token):
    """Unchanged default behavior: FLAG_DESKTOP_LOCAL_TRANSPORT_V12_2 off
    means the resolver is never even consulted - always cloud."""
    ws_id = generate_snowflake_id()
    member = _member(workspace_id=ws_id)
    db = MagicMock()

    with patch.dict("os.environ", {"LIVEKIT_URL": "wss://example.livekit.cloud"}):
        create_realtime_session(
            workspace_id=ws_id,
            data=RealtimeSessionCreateRequest(device_type="desktop"),
            member=member,
            db=db,
        )

    added_session = db.add.call_args[0][0]
    assert added_session.transport == "livekit_cloud"


@patch("integrations.realtime.router.is_local_livekit_healthy", return_value=False)
@patch("integrations.realtime.router.generate_livekit_token", return_value="fake.jwt.token")
@patch("integrations.realtime.router.is_enabled", return_value=True)
def test_create_session_resolves_transport_via_resolver_when_flag_on(mock_is_enabled, mock_token, mock_health):
    """With the flag on and local unhealthy, transport resolves to cloud via resolver."""
    ws_id = generate_snowflake_id()
    member = _member(workspace_id=ws_id)
    db = MagicMock()

    with patch.dict("os.environ", {"LIVEKIT_URL": "wss://example.livekit.cloud"}):
        create_realtime_session(
            workspace_id=ws_id,
            data=RealtimeSessionCreateRequest(device_type="desktop", voice_transport="auto"),
            member=member,
            db=db,
        )

    added_session = db.add.call_args[0][0]
    assert added_session.transport == "livekit_cloud"


@patch("integrations.realtime.router.is_local_livekit_healthy", return_value=True)
@patch("integrations.realtime.router.generate_livekit_token", return_value="fake.local.jwt.token")
@patch("integrations.realtime.router.is_enabled", return_value=True)
def test_create_session_uses_local_transport_when_healthy(mock_is_enabled, mock_token, mock_health):
    """With flag on and local livekit healthy on desktop, resolves to livekit_local and returns local URL."""
    ws_id = generate_snowflake_id()
    member = _member(workspace_id=ws_id)
    db = MagicMock()

    with patch.dict("os.environ", {
        "LIVEKIT_LOCAL_URL": "ws://127.0.0.1:7880",
        "LIVEKIT_LOCAL_API_KEY": "devkey",
        "LIVEKIT_LOCAL_API_SECRET": "secret_local_cosa_desktop_key",
    }):
        result = create_realtime_session(
            workspace_id=ws_id,
            data=RealtimeSessionCreateRequest(device_type="desktop", voice_transport="auto"),
            member=member,
            db=db,
        )

    added_session = db.add.call_args[0][0]
    assert added_session.transport == "livekit_local"
    assert result["livekit_url"] == "ws://127.0.0.1:7880"
    assert result["token"] == "fake.local.jwt.token"
    mock_token.assert_called_once_with(
        room_name=added_session.room_name,
        identity=f"human:{member.user_id}",
        display_name=f"user-{member.user_id}",
        api_key="devkey",
        api_secret="secret_local_cosa_desktop_key",
    )



def test_end_session_rejects_member_from_other_workspace():
    ws_id_a = generate_snowflake_id()
    ws_id_b = generate_snowflake_id()
    member = _member(workspace_id=ws_id_b, user_id=generate_snowflake_id())

    db = MagicMock()
    query = MagicMock()
    query.filter.return_value = query
    query.first.return_value = None
    db.query.return_value = query

    with pytest.raises(HTTPException) as exc_info:
        end_realtime_session(session_id=generate_snowflake_id(), workspace_id=ws_id_a, member=member, db=db)

    assert exc_info.value.status_code == 403


def test_end_session_persists_optional_summary():
    """SAVE_SUMMARY is the default transcript policy (spec §38/§93/§157) -
    the client may optionally supply an end-of-session summary."""
    ws_id = generate_snowflake_id()
    member = _member(workspace_id=ws_id)

    mock_session = MagicMock(spec=RealtimeSession)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = mock_session

    result = end_realtime_session(
        session_id=generate_snowflake_id(),
        workspace_id=ws_id,
        data=RealtimeSessionEndRequest(summary="Founder reviewed mVault status, opened next actions."),
        member=member,
        db=db,
    )

    assert mock_session.summary == "Founder reviewed mVault status, opened next actions."
    assert result["status"] == "ended"


def test_end_session_without_summary_leaves_existing_summary_untouched():
    ws_id = generate_snowflake_id()
    member = _member(workspace_id=ws_id)

    mock_session = MagicMock(spec=RealtimeSession)
    mock_session.summary = None
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = mock_session

    end_realtime_session(session_id=generate_snowflake_id(), workspace_id=ws_id, member=member, db=db)

    assert mock_session.summary is None


def test_end_session_writes_voice_usage_record_with_computed_duration():
    ws_id = generate_snowflake_id()
    session_id = generate_snowflake_id()
    member = _member(workspace_id=ws_id)

    mock_session = MagicMock(spec=RealtimeSession)
    mock_session.id = session_id
    mock_session.model_profile = "gemini_live"
    mock_session.started_at = datetime(2026, 8, 12, 10, 0, 0)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = mock_session

    end_realtime_session(session_id=session_id, workspace_id=ws_id, member=member, db=db)

    # session.ended_at was just set to utcnow() by end_realtime_session itself
    assert mock_session.ended_at > mock_session.started_at

    usage_record = next(
        call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], VoiceUsageRecord)
    )
    assert usage_record.session_id == session_id
    assert usage_record.workspace_id == ws_id
    assert usage_record.model_profile == "gemini_live"
    assert usage_record.duration_seconds == int(
        (mock_session.ended_at - mock_session.started_at).total_seconds()
    )


def test_end_session_usage_record_duration_null_when_never_started():
    """A session that errored before ever going "active" has no started_at -
    duration must stay null rather than computing a bogus number."""
    ws_id = generate_snowflake_id()
    session_id = generate_snowflake_id()
    member = _member(workspace_id=ws_id)

    mock_session = MagicMock(spec=RealtimeSession)
    mock_session.id = session_id
    mock_session.model_profile = "gemini_live"
    mock_session.started_at = None
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = mock_session

    end_realtime_session(session_id=session_id, workspace_id=ws_id, member=member, db=db)

    usage_record = next(
        call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], VoiceUsageRecord)
    )
    assert usage_record.duration_seconds is None


def test_realtime_health_healthy_when_all_configured():
    env = {
        "LIVEKIT_URL": "wss://example.livekit.cloud",
        "LIVEKIT_API_KEY": "key",
        "LIVEKIT_API_SECRET": "secret",
        "GOOGLE_API_KEY": "gkey",
    }
    with patch.dict("os.environ", env, clear=True):
        result = realtime_health()

    assert result == {"status": "HEALTHY", "livekit_configured": True, "gemini_configured": True}


def test_realtime_health_degraded_when_missing_config():
    with patch.dict("os.environ", {}, clear=True):
        result = realtime_health()

    assert result["status"] == "DEGRADED"
    assert result["livekit_configured"] is False
    assert result["gemini_configured"] is False
