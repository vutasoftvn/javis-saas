import io
import uuid
from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock, AsyncMock
import pytest
from fastapi import HTTPException, UploadFile

from app.db.models import WorkspaceMember
from app.modules.chat.router import transcribe_voice


@pytest.mark.asyncio
async def test_transcribe_voice_success(monkeypatch):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id

    file = MagicMock(spec=UploadFile)
    file.filename = "recording.m4a"
    file.read = AsyncMock(return_value=b"fake_audio_bytes")

    async def fake_transcribe(self, audio_bytes, filename="audio.m4a", language="vi"):
        return "Tôi muốn kiểm tra tình trạng vận hành hệ thống COSA."

    monkeypatch.setattr(
        "app.integrations.voice_client.VoiceClient.transcribe", fake_transcribe
    )

    res = await transcribe_voice(
        workspace_id=ws_id,
        file=file,
        language="vi",
        member=member,
    )
    assert "transcript" in res
    assert len(res["transcript"]) > 0


@pytest.mark.asyncio
async def test_transcribe_voice_without_api_key_returns_503(monkeypatch):
    """No fabricated transcript when STT isn't configured - the user said
    something real, and returning a made-up transcript that looks like a
    genuine recognition result would feed a fake user message into the chat
    pipeline (exactly the "fake telemetry" anti-pattern blueprint §108
    forbids). The endpoint must fail loudly (503) instead."""
    ws_id = generate_snowflake_id()

    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id

    file = MagicMock(spec=UploadFile)
    file.filename = "recording.m4a"
    file.read = AsyncMock(return_value=b"fake_audio_bytes")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        await transcribe_voice(
            workspace_id=ws_id,
            file=file,
            language="vi",
            member=member,
        )

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_transcribe_voice_cross_tenant_forbidden():
    ws_id_a = generate_snowflake_id()
    ws_id_b = generate_snowflake_id()

    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id_a

    file = MagicMock(spec=UploadFile)
    file.filename = "recording.m4a"
    file.read = AsyncMock(return_value=b"fake_audio_bytes")

    with pytest.raises(HTTPException) as exc_info:
        await transcribe_voice(
            workspace_id=ws_id_b,
            file=file,
            language="vi",
            member=member,
        )

    assert exc_info.value.status_code == 403
