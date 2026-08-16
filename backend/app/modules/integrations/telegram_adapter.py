import httpx
from typing import Dict, Any, Optional

TELEGRAM_API_BASE = "https://api.telegram.org"


async def test_telegram_connection(bot_token: str) -> Dict[str, Any]:
    """Kiểm tra bot token với Telegram getMe API."""
    clean_token = bot_token.strip()
    if not clean_token:
        return {"status": "error", "message": "Bot token không được để trống"}

    url = f"{TELEGRAM_API_BASE}/bot{clean_token}/getMe"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
            data = resp.json()
            if resp.status_code == 200 and data.get("ok"):
                result = data.get("result", {})
                return {
                    "status": "success",
                    "bot_id": result.get("id"),
                    "bot_username": result.get("username"),
                    "bot_name": result.get("first_name"),
                    "message": f"Kết nối thành công! Bot @{result.get('username')}",
                }
            return {
                "status": "error",
                "message": data.get("description", "Token không hợp lệ hoặc đã bị vô hiệu hóa"),
            }
    except Exception as e:
        return {"status": "error", "message": f"Lỗi kết nối tới máy chủ Telegram: {str(e)}"}


async def send_telegram_message(
    bot_token: str,
    chat_id: str,
    text: str,
    parse_mode: str = "HTML",
) -> Dict[str, Any]:
    """Gửi tin nhắn qua Telegram Bot API."""
    clean_token = bot_token.strip()
    url = f"{TELEGRAM_API_BASE}/bot{clean_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            if resp.status_code == 200 and data.get("ok"):
                return {
                    "status": "sent",
                    "message_id": data.get("result", {}).get("message_id"),
                }
            return {
                "status": "failed",
                "error": data.get("description", f"Telegram API error {resp.status_code}"),
            }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def parse_telegram_update(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Trích xuất thông tin người gửi và nội dung tin nhắn từ webhook Telegram."""
    message = payload.get("message") or payload.get("edited_message") or {}
    chat = message.get("chat", {})
    sender = message.get("from", {})

    return {
        "update_id": payload.get("update_id"),
        "chat_id": str(chat.get("id", "")),
        "sender_id": str(sender.get("id", "")),
        "sender_username": sender.get("username"),
        "sender_name": f"{sender.get('first_name', '')} {sender.get('last_name', '')}".strip(),
        "text": message.get("text") or message.get("caption") or "",
        "message_id": message.get("message_id"),
        "date": message.get("date"),
    }
