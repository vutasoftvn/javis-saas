import os


def read_idle_timeout_seconds() -> float:
    """mCOSA V12.1 §47/§48 - seconds of continuous "away" user state before
    the session is closed. Configurable via env var, not hardcoded."""
    return float(os.environ.get("VOICE_IDLE_TIMEOUT_SECONDS", "120"))


def read_max_session_minutes() -> float:
    """mCOSA V12.1 §47/§48 - hard cap on session duration regardless of
    activity. Configurable via env var, not hardcoded."""
    return float(os.environ.get("VOICE_SESSION_MAX_MINUTES", "30"))


class IdleGuard:
    """Ends the realtime session after `idle_timeout_seconds` of the user
    being *continuously* away - distinct from AgentSession's own built-in
    `user_away_timeout` (default 15s), which only flips `user_state` to
    "away" and does not close anything on its own (spec §47).

    `schedule`/`cancel`/`close` are injected rather than calling
    `asyncio.get_event_loop()` / `session.shutdown()` directly, so this can
    be unit tested without a real event loop or a real AgentSession.
    """

    def __init__(self, *, idle_timeout_seconds: float, schedule, cancel, close):
        self._idle_timeout_seconds = idle_timeout_seconds
        self._schedule = schedule
        self._cancel = cancel
        self._close = close
        self._pending = None

    def on_user_state_changed(self, new_state: str) -> None:
        if self._pending is not None:
            self._cancel(self._pending)
            self._pending = None
        if new_state == "away":
            self._pending = self._schedule(self._idle_timeout_seconds, self._close)
