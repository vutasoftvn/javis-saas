import asyncio
import logging
from typing import List

from fastapi import HTTPException, status

from app.modules.chat.ai_router import ChatProvider, ChatTurn

logger = logging.getLogger(__name__)

_RETRYABLE_HTTP_STATUSES = {"429", "500", "502", "503", "504"}


def _friendly_ai_error_message(error_code: str) -> str:
    if error_code == "provider_http_429":
        return "AI đang bị giới hạn tốc độ (rate limit), vui lòng thử lại sau ít phút"
    if error_code == "provider_not_configured":
        return "AI provider chưa cấu hình"
    if error_code.startswith("provider_http_5"):
        return "AI provider đang gặp sự cố, vui lòng thử lại sau"
    return "AI provider gặp lỗi, vui lòng thử lại hoặc nhập thủ công"


async def consume_ai_stream(provider: ChatProvider, turns: List[ChatTurn], max_retries: int = 2) -> str:
    """Collects a ChatProvider's streamed reply into one string.

    A rate limit (429) or transient server error (5xx) is retried with a
    short backoff before giving up - these usually succeed on the next try
    and shouldn't force the founder to notice and manually retry every time.
    Any other failure, or exhausted retries, raises an HTTPException with a
    Vietnamese message a founder can act on - a raw error_code like
    "provider_http_429" is not actionable for them.
    """
    attempt = 0
    while True:
        chunks: List[str] = []
        error_code = None
        async for event in provider.stream_chat(turns):
            if event.kind == "delta":
                chunks.append(event.content)
            elif event.kind == "failed":
                error_code = event.error_code or "provider_error"
                break
        if error_code is None:
            return "".join(chunks)

        http_status = error_code.replace("provider_http_", "")
        attempt += 1
        if http_status in _RETRYABLE_HTTP_STATUSES and attempt <= max_retries:
            logger.warning("AI stream failed with %s, retrying (%s/%s)", error_code, attempt, max_retries)
            await asyncio.sleep(min(2 ** attempt, 5))
            continue

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_friendly_ai_error_message(error_code),
        )
