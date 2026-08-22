from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger("mcosa.realtime_agent.event_bridge")

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
    """Single place that knows the HOLOGRAM_STATE data-channel envelope."""
    payload = json.dumps({"type": "HOLOGRAM_STATE", "state": state}).encode()
    _fire_and_forget(room.local_participant.publish_data(payload, reliable=True, topic="hologram"))


def publish_ui_command(room, target: str, project_name: str | None) -> None:
    """Single place that knows the UI_COMMAND/OPEN_ROUTE data-channel envelope."""
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
    logger.info("mark_session_active for room %s", room_name)


def mark_session_error(room_name: str) -> None:
    logger.info("mark_session_error for room %s", room_name)
