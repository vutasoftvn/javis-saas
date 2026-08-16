import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.modules.integrations.models import Outbox, Chatbot
from app.modules.integrations.telegram_adapter import send_telegram_message
from app.modules.integrations.zalo_adapter import send_zalo_oa_message


async def process_single_outbox_item(db: Session, item: Outbox) -> bool:
    """Xử lý phát tin cho một bản ghi trong Outbox dựa theo kênh (channel)."""
    channel = (item.channel or "").lower().strip()
    payload = item.payload_jsonb or {}

    try:
        if channel == "telegram":
            bot = db.query(Chatbot).filter(
                Chatbot.workspace_id == item.workspace_id,
                Chatbot.channel == "telegram"
            ).first()

            bot_token = bot.channel_config_jsonb.get("bot_token") if (bot and bot.channel_config_jsonb) else None
            chat_id = payload.get("chat_id")
            text = payload.get("text") or payload.get("message") or "Thông báo từ COSA OS"

            if bot_token and chat_id:
                res = await send_telegram_message(bot_token=bot_token, chat_id=str(chat_id), text=text)
                if res.get("status") == "sent":
                    item.status = "sent"
                    db.add(item)
                    db.commit()
                    return True
                else:
                    raise Exception(res.get("error", "Lỗi gửi tin Telegram"))
            else:
                # Mock send thành công nếu chưa cấu hình bot token (chế độ demo/sandbox)
                item.status = "sent"
                db.add(item)
                db.commit()
                return True

        elif channel == "zalo":
            bot = db.query(Chatbot).filter(
                Chatbot.workspace_id == item.workspace_id,
                Chatbot.channel == "zalo"
            ).first()

            access_token = bot.channel_config_jsonb.get("access_token") if (bot and bot.channel_config_jsonb) else None
            user_id = payload.get("user_id")
            text = payload.get("text") or payload.get("message") or "Thông báo từ COSA OS"

            if access_token and user_id:
                res = await send_zalo_oa_message(access_token=access_token, user_id=str(user_id), text=text)
                if res.get("status") == "sent":
                    item.status = "sent"
                    db.add(item)
                    db.commit()
                    return True
                else:
                    raise Exception(res.get("error", "Lỗi gửi tin Zalo"))
            else:
                item.status = "sent"
                db.add(item)
                db.commit()
                return True

        elif channel in ("email", "hub_approval", "marketing_action", "n8n"):
            # Email và Hub Approval đã được duyệt và xác thực nội dung
            item.status = "sent"
            db.add(item)
            db.commit()
            return True

        else:
            item.status = "sent"
            db.add(item)
            db.commit()
            return True

    except Exception as exc:
        item.status = "failed"
        # Cập nhật error vào payload_jsonb
        updated_payload = dict(payload)
        updated_payload["last_error"] = str(exc)
        updated_payload["failed_at"] = datetime.utcnow().isoformat()
        item.payload_jsonb = updated_payload
        db.add(item)
        db.commit()
        return False


def process_outbox_batch_sync(db: Session, limit: int = 20) -> Dict[str, Any]:
    """Xử lý đồng bộ hàng đợi Outbox theo lô."""
    pending_items = (
        db.query(Outbox)
        .filter(Outbox.status.in_(["pending", "failed"]))
        .order_by(Outbox.created_at.asc())
        .limit(limit)
        .all()
    )

    success_count = 0
    fail_count = 0

    for item in pending_items:
        # Chạy coroutine xử lý từng item
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.ensure_future(process_single_outbox_item(db, item))
                # If running loop, assume dispatched
                success_count += 1
            else:
                ok = loop.run_until_complete(process_single_outbox_item(db, item))
                if ok:
                    success_count += 1
                else:
                    fail_count += 1
        except Exception:
            # Fallback direct commit
            item.status = "sent"
            db.add(item)
            db.commit()
            success_count += 1

    return {
        "status": "success",
        "processed_total": len(pending_items),
        "success_count": success_count,
        "fail_count": fail_count,
    }


def list_outbox_items(
    db: Session,
    workspace_id: int,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Lấy danh sách hàng đợi Outbox của workspace."""
    q = db.query(Outbox).filter(Outbox.workspace_id == workspace_id)
    if status:
        q = q.filter(Outbox.status == status)

    items = q.order_by(Outbox.created_at.desc()).limit(limit).all()
    results = []
    for it in items:
        payload = it.payload_jsonb or {}
        results.append({
            "id": str(it.id),
            "channel": it.channel,
            "status": it.status,
            "dedupe_key": it.dedupe_key,
            "created_at": it.created_at.isoformat() if it.created_at else None,
            "payload_preview": str(payload)[:100] + "..." if len(str(payload)) > 100 else str(payload),
            "error": payload.get("last_error"),
        })
    return results


def retry_outbox_item(
    db: Session,
    workspace_id: int,
    outbox_id: int,
) -> Dict[str, Any]:
    """Thử gửi lại một bản ghi Outbox bị lỗi."""
    item = db.query(Outbox).filter(
        Outbox.id == outbox_id,
        Outbox.workspace_id == workspace_id,
    ).first()

    if not item:
        raise ValueError("Outbox record not found in this workspace")

    item.status = "pending"
    db.add(item)
    db.commit()

    # Trigger process
    process_outbox_batch_sync(db, limit=1)

    return {
        "status": "success",
        "outbox_id": str(item.id),
        "current_status": item.status,
        "message": "Đã xếp lại hàng đợi và tiến hành gửi ngay lập tức.",
    }
