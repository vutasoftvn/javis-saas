import os
import io
import httpx
from typing import Optional


class VoiceClient:
    """STT Voice Client Adapter - Chuyển đổi giọng nói thành văn bản (§34, §104)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.environ.get("WHISPER_MODEL", "whisper-1")

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.m4a",
        language: Optional[str] = "vi",
    ) -> str:
        if not audio_bytes:
            return ""

        if not self.api_key:
            # KHÔNG fabricate transcript giả - người dùng đã nói một câu thật,
            # trả về một câu bịa khác rồi đẩy vào chat pipeline như thể đó là
            # lời họ nói là chính xác loại "fake telemetry" blueprint §108
            # cấm. Phải báo lỗi rõ ràng để endpoint trả 503 trung thực.
            raise RuntimeError("STT provider not configured (missing OPENAI_API_KEY)")

        url = f"{self.base_url}/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        files = {
            "file": (filename, audio_bytes, "audio/m4a"),
        }
        data = {
            "model": self.model,
        }
        if language:
            data["language"] = language

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, data=data, files=files)
            if resp.status_code == 200:
                result = resp.json()
                return result.get("text", "").strip()
            else:
                return f"[Lỗi nhận dạng giọng nói: {resp.status_code}]"
