import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from session_guards import (
    IdleGuard,
    read_idle_timeout_seconds,
    read_max_session_minutes,
)


def test_read_idle_timeout_seconds_default():
    with patch.dict(os.environ, {}, clear=True):
        assert read_idle_timeout_seconds() == 120.0


def test_read_idle_timeout_seconds_env_override():
    with patch.dict(os.environ, {"VOICE_IDLE_TIMEOUT_SECONDS": "45"}, clear=True):
        assert read_idle_timeout_seconds() == 45.0


def test_read_max_session_minutes_default():
    with patch.dict(os.environ, {}, clear=True):
        assert read_max_session_minutes() == 30.0


def test_read_max_session_minutes_env_override():
    with patch.dict(os.environ, {"VOICE_SESSION_MAX_MINUTES": "10"}, clear=True):
        assert read_max_session_minutes() == 10.0


def _make_guard():
    scheduled = []
    cancelled = []
    closed = []

    def schedule(delay, callback):
        handle = object()
        scheduled.append((delay, callback, handle))
        return handle

    def cancel(handle):
        cancelled.append(handle)

    def close():
        closed.append(True)

    guard = IdleGuard(idle_timeout_seconds=99.0, schedule=schedule, cancel=cancel, close=close)
    return guard, scheduled, cancelled, closed, close


def test_idle_guard_schedules_close_when_user_goes_away():
    guard, scheduled, cancelled, closed, close = _make_guard()

    guard.on_user_state_changed("away")

    assert len(scheduled) == 1
    delay, callback, _ = scheduled[0]
    assert delay == 99.0
    assert callback is close
    assert not cancelled
    assert not closed


def test_idle_guard_cancels_pending_close_when_user_returns():
    guard, scheduled, cancelled, closed, _close = _make_guard()

    guard.on_user_state_changed("away")
    guard.on_user_state_changed("listening")

    assert len(scheduled) == 1
    assert len(cancelled) == 1
    assert cancelled[0] is scheduled[0][2]


def test_idle_guard_does_not_schedule_for_non_away_states():
    guard, scheduled, cancelled, closed, _close = _make_guard()

    guard.on_user_state_changed("listening")
    guard.on_user_state_changed("speaking")

    assert scheduled == []
    assert cancelled == []


def test_idle_guard_replaces_pending_timer_on_repeated_away():
    """A second "away" event (e.g. a brief listening blip in between)
    must not leave two competing timers - only the latest one should fire."""
    guard, scheduled, cancelled, closed, _close = _make_guard()

    guard.on_user_state_changed("away")
    guard.on_user_state_changed("away")

    assert len(scheduled) == 2
    assert len(cancelled) == 1
    assert cancelled[0] is scheduled[0][2]
