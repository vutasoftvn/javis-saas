import asyncio
import json
import logging
import os
import sys
from datetime import datetime

# services/realtime_agent is a separate deploy unit from backend/app, but
# reuses its DB session/model directly (SessionLocal(), no internal HTTP hop)
# rather than duplicating the persistence logic here - same pattern as
# tools.py.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.modules.realtime.models import RealtimeEvent, RealtimeSession  # noqa: E402

logger = logging.getLogger("mcosa.realtime_agent.event_bridge")

# publish_hologram_state/publish_ui_command are called from sync callbacks
# (session.on("agent_state_changed") etc. in agent.py, invoked directly by
# livekit-agents, not awaited) but LocalParticipant.publish_data is a
# coroutine - calling it directly without awaiting or scheduling it just
# builds the coroutine object and silently never runs its body (Python logs
# "coroutine was never awaited" but does not raise), so every hologram state
# update was being dropped and the client UI never left its initial state.
# asyncio.create_task() needs a strong reference kept until it finishes or
# the task can be garbage-collected mid-flight, hence the module-level set.
_pending_publish_tasks: set[asyncio.Task] = set()


def _fire_and_forget(coro) -> None:
    task = asyncio.create_task(coro)
    _pending_publish_tasks.add(task)

    def _on_done(t: asyncio.Task) -> None:
        _pending_publish_tasks.discard(t)
        if not t.cancelled() and (exc := t.exception()) is not None:
            logger.warning("publish_data failed: %s", exc)

    task.add_done_callback(_on_done)


def publish_hologram_state(room, state: str) -> None:
    """Single place that knows the HOLOGRAM_STATE data-channel envelope
    (mCOSA V12.1 §11-12) - previously duplicated between agent.py and
    tools.py."""
    payload = json.dumps({"type": "HOLOGRAM_STATE", "state": state}).encode()
    _fire_and_forget(room.local_participant.publish_data(payload, reliable=True, topic="hologram"))


def publish_ui_command(room, target: str, project_name: str | None) -> None:
    """Single place that knows the UI_COMMAND/OPEN_ROUTE data-channel
    envelope (mCOSA V12.1 §57-58)."""
    payload = json.dumps(
        {
            "type": "UI_COMMAND",
            "command": "OPEN_ROUTE",
            "target": target,
            "params": {"project_name": project_name},
        }
    ).encode()
    _fire_and_forget(room.local_participant.publish_data(payload, reliable=True, topic="hologram"))


def mark_session_active(room_name: str) -> None:
    """Flip RealtimeSession.status to "active" once the AgentSession has
    actually started - this is the only place that can truthfully say a
    human is now talking to a live agent. Before this, router.py only ever
    wrote "creating"/"ended" and status never moved past "creating" even for
    a fully working session.

    Guarded against a session that already ended (e.g. client called
    /sessions/{id}/end while the agent was still connecting) so this never
    resurrects a session the user already closed. Also appends a
    SESSION_CONNECTED RealtimeEvent (mCOSA V12.1 §37) - only when the
    transition actually happens, not on the no-op paths above.
    """
    db = SessionLocal()
    try:
        session = db.query(RealtimeSession).filter(RealtimeSession.room_name == room_name).first()
        if session is None:
            logger.warning("mark_session_active: no RealtimeSession for room %s", room_name)
            return
        if session.status == "ended":
            return
        session.status = "active"
        session.started_at = datetime.utcnow()
        db.add(RealtimeEvent(session_id=session.id, event_type="SESSION_CONNECTED"))
        db.commit()
    finally:
        db.close()


def mark_session_error(room_name: str) -> None:
    """Flip RealtimeSession.status to "error" when the agent session raises.
    Same end-already-wins guard and SESSION_ERROR RealtimeEvent append as
    mark_session_active."""
    db = SessionLocal()
    try:
        session = db.query(RealtimeSession).filter(RealtimeSession.room_name == room_name).first()
        if session is None:
            logger.warning("mark_session_error: no RealtimeSession for room %s", room_name)
            return
        if session.status == "ended":
            return
        session.status = "error"
        db.add(RealtimeEvent(session_id=session.id, event_type="SESSION_ERROR"))
        db.commit()
    finally:
        db.close()
