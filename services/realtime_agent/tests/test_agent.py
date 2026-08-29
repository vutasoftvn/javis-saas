import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import _build_turn_handling, _parse_room_name


def test_parse_room_name_extracts_workspace_and_user_id():
    workspace_id, user_id = _parse_room_name("cosa-123-456-789")
    assert workspace_id == 123
    assert user_id == 456


def test_parse_room_name_rejects_unexpected_format():
    with pytest.raises(ValueError):
        _parse_room_name("not-a-cosa-room")


def test_build_turn_handling_defaults_match_sdk_defaults():
    """Unset env vars must reproduce livekit-agents' own TurnHandlingOptions
    defaults exactly, so deploying without any VOICE_* env vars set changes
    nothing versus not passing turn_handling at all."""
    with patch.dict(os.environ, {}, clear=True):
        result = _build_turn_handling()

    assert result == {
        "endpointing": {"min_delay": 0.5, "max_delay": 3.0},
        "interruption": {"enabled": True, "min_duration": 0.5},
    }


def test_build_turn_handling_reads_env_overrides():
    env = {
        "VOICE_MIN_ENDPOINTING_DELAY": "0.2",
        "VOICE_MAX_ENDPOINTING_DELAY": "1.5",
        "VOICE_INTERRUPTION_ENABLED": "false",
        "VOICE_INTERRUPTION_MIN_DURATION": "0.8",
    }
    with patch.dict(os.environ, env, clear=True):
        result = _build_turn_handling()

    assert result == {
        "endpointing": {"min_delay": 0.2, "max_delay": 1.5},
        "interruption": {"enabled": False, "min_duration": 0.8},
    }
