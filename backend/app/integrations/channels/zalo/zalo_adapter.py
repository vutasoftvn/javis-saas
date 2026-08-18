import httpx
from typing import Dict, Any, Optional

ZALO_OPENAPI_BASE = "https://openapi.zalo.me/v3.0"


async def test_zalo_connection(
    app_id: str,
    secret_key: str,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Kiểm tra cấu hình Zalo OA / App Secret."""
    if not app_id.strip() or not secret_key.strip():
        return {"status": "error", "message": "App ID và Secret Key không được để trống"}

    if not access_token:
        # Nếu chưa có token, xác thực sơ bộ định dạng
        return {
            "status": "success",
            "app_id": app_id,
            "message": "Cấu hình Zalo OA App ID và Secret hợp lệ. Vui lòng quét mã QR hoặc cấp Access Token.",
        }

    url = f"{ZALO_OPENAPI_BASE}/oa/getoa"
    headers = {"access_token": access_token}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=headers)
            data = resp.json()
            if data.get("error") == 0:
                oa_data = data.get("data", {})
                return {
                    "status": "success",
                    "oa_id": oa_data.get("oa_id"),
                    "name": oa_data.get("name"),
                    "description": oa_data.get("description"),
                    "message": f"Kết nối Zalo OA thành công: {oa_data.get('name')}",
                }
            return {
                "status": "error",
                "message": data.get("message", "Access Token không hợp lệ hoặc đã hết hạn"),
            }
    except Exception as e:
        return {"status": "error", "message": f"Lỗi kết nối tới Zalo OpenAPI: {str(e)}"}


async def send_zalo_oa_message(
    access_token: str,
    user_id: str,
    text: str,
) -> Dict[str, Any]:
    """Gửi tin nhắn phản hồi qua Zalo OA."""
    url = f"{ZALO_OPENAPI_BASE}/oa/message/cs"
    headers = {
        "access_token": access_token,
        "Content-Type": "application/json",
    }
    payload = {
        "recipient": {"user_id": user_id},
        "message": {"text": text},
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            data = resp.json()
            if data.get("error") == 0:
                return {
                    "status": "sent",
                    "message_id": data.get("data", {}).get("message_id"),
                }
            return {
                "status": "failed",
                "error": data.get("message", f"Zalo error code {data.get('error')}"),
            }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def parse_zalo_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Trích xuất thông tin người dùng và tin nhắn từ Zalo OA Webhook."""
    event_name = payload.get("event_name", "")
    sender = payload.get("sender", {})
    recipient = payload.get("recipient", {})
    message = payload.get("message", {})

    return {
        "event_name": event_name,
        "app_id": payload.get("app_id"),
        "user_id": str(sender.get("id", "")),
        "oa_id": str(recipient.get("id", "")),
        "text": message.get("text", ""),
        "message_id": message.get("msg_id"),
        "timestamp": payload.get("timestamp"),
    }
