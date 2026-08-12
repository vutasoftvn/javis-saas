import asyncio
import logging
import os

from livekit.agents import Agent, AgentSession, JobContext
from livekit.agents.voice.events import (
    AgentStateChangedEvent,
    ToolExecutionUpdatedEvent,
    UserStateChangedEvent,
)
from livekit.plugins.google.beta import realtime as google_realtime

from event_bridge import mark_session_active, mark_session_error, publish_hologram_state
from session_context import build_system_instructions
from session_guards import IdleGuard, read_idle_timeout_seconds, read_max_session_minutes
from tools import build_tools

logger = logging.getLogger("mcosa.realtime_agent")

# AgentSession's built-in AgentState values map almost 1:1 onto the Hologram
# runtime states the Flutter side already understands (mCOSA V12.1 §11-12).
_AGENT_STATE_TO_HOLOGRAM = {
    "initializing": "IDLE",
    "idle": "IDLE",
    "listening": "LISTENING",
    "thinking": "THINKING",
    "speaking": "SPEAKING",
}


def _build_turn_handling() -> dict:
    """Turn/endpointing/interruption tuning (mCOSA V12.1 §13-14), read from
    env vars rather than hardcoded - defaults match livekit-agents'
    (>=1.6, pinned in requirements.txt) own TurnHandlingOptions defaults, so
    leaving these unset changes nothing. Vietnamese barge-in latency should
    be benchmarked independently per spec §14 and tuned by setting these env
    vars, not by editing this function.
    """
    return {
        "endpointing": {
            "min_delay": float(os.environ.get("VOICE_MIN_ENDPOINTING_DELAY", "0.5")),
            "max_delay": float(os.environ.get("VOICE_MAX_ENDPOINTING_DELAY", "3.0")),
        },
        "interruption": {
            "enabled": os.environ.get("VOICE_INTERRUPTION_ENABLED", "true").strip().lower() != "false",
            "min_duration": float(os.environ.get("VOICE_INTERRUPTION_MIN_DURATION", "0.5")),
        },
    }


def _parse_room_name(room_name: str) -> tuple[int, int]:
    """room_name format: cosa-{workspace_id}-{user_id}-{snowflake} (router.py).

    Parsing tenancy straight from the room name avoids a second
    RoomServiceClient metadata round-trip just to hand the agent its
    workspace/user scope.
    """
    parts = room_name.split("-")
    if len(parts) < 4 or parts[0] != "cosa":
        raise ValueError(f"Unexpected room name format: {room_name}")
    return int(parts[1]), int(parts[2])


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()

    workspace_id, user_id = _parse_room_name(ctx.room.name)
    display_name = f"user-{user_id}"

    session = AgentSession(
        llm=google_realtime.RealtimeModel(
            voice="Puck",
        ),
        turn_handling=_build_turn_handling(),
    )

    @session.on("agent_state_changed")
    def _on_agent_state_changed(event: AgentStateChangedEvent) -> None:
        hologram_state = _AGENT_STATE_TO_HOLOGRAM.get(event.new_state, "IDLE")
        publish_hologram_state(ctx.room, hologram_state)

    loop = asyncio.get_event_loop()
    idle_guard = IdleGuard(
        idle_timeout_seconds=read_idle_timeout_seconds(),
        schedule=loop.call_later,
        cancel=lambda handle: handle.cancel(),
        close=lambda: session.shutdown(drain=False),
    )

    @session.on("user_state_changed")
    def _on_user_state_changed(event: UserStateChangedEvent) -> None:
        # Barge-in: user starts speaking while the agent was speaking - the
        # RealtimeModel already stops the agent's audio on its own (built-in
        # interruption handling); we only need to reflect it in the UI.
        if event.new_state == "speaking":
            publish_hologram_state(ctx.room, "LISTENING")
        # Idle timeout (mCOSA V12.1 §47/§48): distinct from AgentSession's own
        # short user_away_timeout, which only flips this state - it does not
        # end the session on its own.
        idle_guard.on_user_state_changed(event.new_state)

    @session.on("tool_execution_updated")
    def _on_tool_execution_updated(event: ToolExecutionUpdatedEvent) -> None:
        # Narrower than agent_state_changed's "thinking" - flashes a distinct
        # RETRIEVING/ACTING state while get_ceo_brief/get_next_best_actions
        # are actually running, per the spec's Hologram state list (§11-12).
        if event.update.type == "tool_call_started":
            publish_hologram_state(ctx.room, "RETRIEVING")
        elif event.update.type == "tool_call_ended":
            publish_hologram_state(ctx.room, "ACTING" if event.update.status == "done" else "ERROR")

    @session.on("error")
    def _on_error(event) -> None:
        logger.error("[realtime_agent] session error: %s", event)
        publish_hologram_state(ctx.room, "ERROR")
        mark_session_error(ctx.room.name)

    agent = Agent(
        instructions=build_system_instructions(workspace_id, display_name),
        tools=build_tools(room=ctx.room, workspace_id=workspace_id, user_id=user_id),
    )

    await session.start(agent=agent, room=ctx.room)
    # session.start() only returns once the agent has actually joined and is
    # ready - the first truthful point to say RealtimeSession.status="active"
    # (previously nothing ever set this past "creating").
    mark_session_active(ctx.room.name)

    # Hard cap regardless of activity (mCOSA V12.1 §47/§48) - do not leave
    # realtime sessions connected indefinitely even if the user stays active.
    loop.call_later(read_max_session_minutes() * 60, lambda: session.shutdown(drain=False))


def prewarm(proc) -> None:
    pass
