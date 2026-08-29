import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from event_bridge import (
    mark_session_active,
    mark_session_error,
    publish_hologram_state,
    publish_ui_command,
)


def test_publish_hologram_state_sends_expected_payload():
    room = MagicMock()
    room.local_participant.publish_data = AsyncMock()

    async def _run():
        publish_hologram_state(room, "LISTENING")
        await asyncio.sleep(0)

    asyncio.run(_run())

    room.local_participant.publish_data.assert_called_once()
    payload, kwargs = room.local_participant.publish_data.call_args
    assert b'"type": "HOLOGRAM_STATE"' in payload[0]
    assert b'"state": "LISTENING"' in payload[0]
    assert kwargs == {"reliable": True, "topic": "hologram"}


def test_publish_ui_command_sends_expected_payload():
    room = MagicMock()
    room.local_participant.publish_data = AsyncMock()

    async def _run():
        publish_ui_command(room, "tasks", "mVault")
        await asyncio.sleep(0)

    asyncio.run(_run())

    room.local_participant.publish_data.assert_called_once()
    payload, kwargs = room.local_participant.publish_data.call_args
    assert b'"type": "UI_COMMAND"' in payload[0]
    assert b'"command": "OPEN_ROUTE"' in payload[0]
    assert b'"target": "tasks"' in payload[0]
    assert kwargs == {"reliable": True, "topic": "hologram"}


def test_mark_session_active_runs_without_legacy_db():
    mark_session_active("cosa-1-2-3")


def test_mark_session_error_runs_without_legacy_db():
    mark_session_error("cosa-1-2-3")
