import asyncio
import json
import logging
import os

from event_bridge import mark_session_active, mark_session_error, publish_hologram_state
from livekit.agents import Agent, AgentSession, JobContext
from livekit.agents.llm import ChatMessage
from livekit.agents.utils.audio import audio_frames_from_file
from livekit.agents.voice.events import (
    AgentStateChangedEvent,
    ConversationItemAddedEvent,
    MetricsCollectedEvent,
    ToolExecutionUpdatedEvent,
    UserInputTranscribedEvent,
    UserStateChangedEvent,
)
from livekit.plugins.google.beta import realtime as google_realtime
from services_client import ServicesClient
from session_context import build_system_instructions
from session_guards import IdleGuard, read_idle_timeout_seconds, read_max_session_minutes
from voice_tools import build_tools

logger = logging.getLogger("mcosa.realtime_agent")

# Must match scripts/generate_greeting_audio.py's GREETING_TEXT/OUTPUT_PATH.
GREETING_TEXT = "Xin chào, tôi là COSA, tôi có thể giúp gì cho bạn?"
GREETING_AUDIO_PATH = os.path.join(os.path.dirname(__file__), "assets", "greeting_vi.wav")

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


async def _resolve_conversation_id(
    ctx: JobContext,
    workspace_id: int,
    user_id: int,
    client: ServicesClient,
) -> str:
    """Resolves conversation_id from session metadata or creates a new conversation via Agent API (§17.3)."""
    raw_meta = getattr(ctx.room, "metadata", None) or ""
    if not raw_meta and hasattr(ctx, "job"):
        raw_meta = getattr(ctx.job, "metadata", None) or ""

    if raw_meta:
        try:
            parsed = json.loads(raw_meta)
            if isinstance(parsed, dict) and parsed.get("conversation_id"):
                return str(parsed["conversation_id"])
        except Exception:
            cleaned = raw_meta.strip()
            if cleaned:
                return cleaned

    try:
        res = await client.create_conversation(
            workspace_id=workspace_id,
            user_id=user_id,
            title="Voice Conversation",
            active_agent_profile="founder_assistant",
        )
        return str(res.get("id") or f"voice-conv-{workspace_id}-{user_id}")
    except Exception as exc:
        logger.warning(f"Could not auto-create conversation via Agent API: {exc}. Using fallback ID.")
        return f"voice-conv-{workspace_id}-{user_id}"


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()

    workspace_id, user_id = _parse_room_name(ctx.room.name)
    display_name = f"user-{user_id}"
    services_client = ServicesClient()

    conversation_id = await _resolve_conversation_id(ctx, workspace_id, user_id, services_client)

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
        if event.update.type == "tool_call_started":
            publish_hologram_state(ctx.room, "RETRIEVING")
        elif event.update.type == "tool_call_ended":
            publish_hologram_state(ctx.room, "ACTING" if event.update.status == "done" else "ERROR")

    @session.on("error")
    def _on_error(event) -> None:
        logger.error("[realtime_agent] session error: %s", event)
        publish_hologram_state(ctx.room, "ERROR")
        mark_session_error(ctx.room.name)

    @session.on("metrics_collected")
    def _on_metrics_collected(event: MetricsCollectedEvent) -> None:
        m = event.metrics
        ttft = getattr(m, "ttft", None)
        logger.info(
            "[realtime_agent] metrics type=%s label=%s ttft=%s duration=%s",
            m.type,
            m.label,
            ttft,
            getattr(m, "duration", None),
        )

    # Record user voice transcript in Agent API Message repository (§17.3)
    @session.on("user_input_transcribed")
    def _on_user_input_transcribed(event: UserInputTranscribedEvent) -> None:
        if event.is_final and event.transcript:
            logger.info("[realtime_agent] STT (user): %r", event.transcript)
            asyncio.create_task(
                services_client.send_message(
                    conversation_id=conversation_id,
                    content=event.transcript,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    role="user",
                )
            )

    # Record assistant voice response in Agent API Message repository (§17.3)
    @session.on("conversation_item_added")
    def _on_conversation_item_added(event: ConversationItemAddedEvent) -> None:
        item = event.item
        if isinstance(item, ChatMessage):
            logger.info(
                "[realtime_agent] conversation item role=%s text=%r",
                item.role,
                item.text_content,
            )
            if item.role == "assistant" and item.text_content:
                asyncio.create_task(
                    services_client.send_message(
                        conversation_id=conversation_id,
                        content=item.text_content,
                        workspace_id=workspace_id,
                        user_id=user_id,
                        role="assistant",
                    )
                )

    agent = Agent(
        instructions=build_system_instructions(workspace_id, display_name),
        tools=build_tools(
            room=ctx.room,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            client=services_client,
        ),
    )

    await session.start(agent=agent, room=ctx.room)
    mark_session_active(ctx.room.name)

    try:
        session.say(GREETING_TEXT, audio=audio_frames_from_file(GREETING_AUDIO_PATH))
    except Exception as e:
        logger.warning(f"Failed to play initial greeting: {e}")

    # Hard cap regardless of activity (mCOSA V12.1 §47/§48)
    loop.call_later(read_max_session_minutes() * 60, lambda: session.shutdown(drain=False))


def prewarm(proc) -> None:
    pass
