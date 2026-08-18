import os
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.core.feature_flags import FLAG_DESKTOP_LOCAL_TRANSPORT_V12_2, is_enabled
from app.core.snowflake import generate_snowflake_id
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.integrations.realtime.models import RealtimeSession, VoiceUsageRecord
from app.integrations.realtime.token_service import generate_livekit_token
from app.integrations.realtime.transport_resolver import RealtimeTransportResolver

router = APIRouter()


class RealtimeSessionCreateRequest(BaseModel):
    device_type: Literal["desktop", "mobile", "web"]
    # AUTO by default (spec §107-109) - the founder should not need to think
    # in transport names during normal use.
    voice_transport: Literal["auto", "local", "cloud"] = "auto"


class RealtimeSessionEndRequest(BaseModel):
    # Transcript retention default is SAVE_SUMMARY (spec §38/§93/§157): the
    # client may optionally supply an end-of-session summary; raw transcript
    # is never accepted/persisted here.
    summary: Optional[str] = None


import httpx

def is_local_livekit_healthy(health_url: Optional[str] = None) -> bool:
    """Checks if local LiveKit server is running and reachable."""
    candidates = []
    if health_url:
        candidates.append(health_url)
    custom_http = os.environ.get("LIVEKIT_LOCAL_HTTP_URL")
    if custom_http:
        candidates.append(custom_http)
    candidates.extend(["http://livekit:7880", "http://127.0.0.1:7880", "http://localhost:7880"])

    for url in candidates:
        try:
            with httpx.Client(timeout=0.5) as client:
                resp = client.get(url)
                if resp.status_code < 500:
                    return True
        except Exception:
            continue
    return False


@router.post("/sessions")
def create_realtime_session(
    workspace_id: int,
    data: RealtimeSessionCreateRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    # Room name carries workspace_id/user_id so services/realtime_agent can
    # parse tenancy straight from ctx.room.name without an extra RoomServiceClient
    # metadata round-trip (mCOSA V12.1 §64).
    room_name = f"cosa-{workspace_id}-{member.user_id}-{generate_snowflake_id()}"

    # Local LiveKit server infrastructure (mCOSA V12.2 §101-102)
    local_available = is_local_livekit_healthy()
    if is_enabled(db, FLAG_DESKTOP_LOCAL_TRANSPORT_V12_2, workspace_id):
        decision = RealtimeTransportResolver().resolve(
            device_type=data.device_type,
            setting=data.voice_transport,
            local_available=local_available,
        )
        transport = decision.transport
    else:
        transport = "livekit_cloud"

    session = RealtimeSession(
        workspace_id=workspace_id,
        user_id=member.user_id,
        device_type=data.device_type,
        room_name=room_name,
        status="creating",
        transport=transport,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    if transport == "livekit_local":
        livekit_url = os.environ.get("LIVEKIT_LOCAL_URL", "ws://127.0.0.1:7880")
        api_key = os.environ.get("LIVEKIT_LOCAL_API_KEY", "devkey")
        api_secret = os.environ.get("LIVEKIT_LOCAL_API_SECRET", "secret_local_cosa_desktop_key")
    else:
        livekit_url = os.environ["LIVEKIT_URL"]
        api_key = os.environ["LIVEKIT_API_KEY"]
        api_secret = os.environ["LIVEKIT_API_SECRET"]

    token = generate_livekit_token(
        room_name=room_name,
        identity=f"human:{member.user_id}",
        display_name=f"user-{member.user_id}",
        api_key=api_key,
        api_secret=api_secret,
    )

    return {
        "session_id": str(session.id),
        "room_name": room_name,
        "livekit_url": livekit_url,
        "token": token,
        "status": session.status,
    }


@router.post("/sessions/{session_id}/end")
def end_realtime_session(
    session_id: int,
    workspace_id: int,
    data: RealtimeSessionEndRequest = RealtimeSessionEndRequest(),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    # Keep the write boundary self-contained. FastAPI's membership dependency
    # normally guarantees this, but internal callers and future adapters must
    # not be able to end another workspace's realtime session by supplying its
    # workspace ID directly.
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    # Filter workspace_id directly in the query (not just compare
    # member.workspace_id) so a session_id belonging to another workspace is
    # indistinguishable from a non-existent one - no cross-tenant existence leak.
    session = (
        db.query(RealtimeSession)
        .filter(RealtimeSession.id == session_id, RealtimeSession.workspace_id == workspace_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.status = "ended"
    session.ended_at = datetime.utcnow()
    if data.summary is not None:
        session.summary = data.summary

    # Usage tracking (spec §46/§56/§82) - one record per session, written
    # once here rather than incrementally, since duration is only known once
    # the session has actually ended. No pricing model wired up yet, so
    # estimated_cost stays null rather than guessing a number.
    duration_seconds = None
    if session.started_at is not None:
        duration_seconds = int((session.ended_at - session.started_at).total_seconds())
    db.add(
        VoiceUsageRecord(
            session_id=session.id,
            workspace_id=workspace_id,
            duration_seconds=duration_seconds,
            model_profile=session.model_profile,
        )
    )
    db.commit()

    return {"session_id": str(session.id), "status": session.status}


@router.get("/health")
def realtime_health():
    """Config sanity check (spec §180-style health surface, scoped down for
    Part B) - not a live worker/agent ping, just whether the LiveKit/Gemini
    credentials this whole feature depends on are actually configured."""
    livekit_configured = bool(os.environ.get("LIVEKIT_URL")) and bool(os.environ.get("LIVEKIT_API_KEY")) and bool(
        os.environ.get("LIVEKIT_API_SECRET")
    )
    gemini_configured = bool(os.environ.get("GOOGLE_API_KEY"))

    return {
        "status": "HEALTHY" if (livekit_configured and gemini_configured) else "DEGRADED",
        "livekit_configured": livekit_configured,
        "gemini_configured": gemini_configured,
    }
