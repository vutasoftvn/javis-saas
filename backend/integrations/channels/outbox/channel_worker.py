import asyncio
import logging
import httpx
from typing import Dict, Set
from sqlalchemy.orm import Session

from db.session import SessionLocal
from db.models import Chatbot

logger = logging.getLogger(__name__)

# Lưu offset & deduplication cache ngầm trong bộ nhớ
telegram_offsets: Dict[str, int] = {}
processed_zalo_msgs: Set[str] = set()


async def _generate_ai_reply(text: str) -> str:
    """Gọi AI Router (DeepSeek/OpenRouter) để tạo câu phản hồi tự nhiên, chuyên nghiệp."""
    try:
        from workforce.chat.ai_router import AIRouter, ChatTurn
        from workforce.chat.providers import build_provider
        from workforce.chat.model_registry import DEFAULT_PROVIDER, DEFAULT_MODEL

        router = AIRouter(build_provider)
        turns = [
            ChatTurn(
                role="system",
                content=(
                    "Bạn là trợ lý AI tư vấn khách hàng thông minh của COSA OS. "
                    "Hãy trả lời ngắn gọn, tự nhiên, thân thiện và chuyên nghiệp bằng tiếng Việt. "
                    "Không tự nhận mình là mẫu câu hay bot thử nghiệm."
                ),
            ),
            ChatTurn(role="user", content=text),
        ]
        reply_content = ""
        async for event in router.stream_chat(turns, DEFAULT_PROVIDER, DEFAULT_MODEL):
            if event.kind == "delta":
                reply_content += event.content
            elif event.kind == "failed":
                logger.warning(f"AI response generation failed for channel message: {event.error_code}")
                break

        if reply_content.strip():
            return reply_content.strip()
    except Exception as exc:
        logger.error(f"Error calling AI router in channel worker: {exc}")

    return "Chào bạn! Tôi là Trợ lý AI của COSA OS. Rất vui được hỗ trợ bạn. Bạn cần thông tin gì ạ?"


async def process_telegram_bot(client: httpx.AsyncClient, bot: Chatbot, db: Session):
    config = bot.channel_config_jsonb or {}
    token = config.get("bot_token", "").strip()
    if not token or not config.get("is_enabled", False):
        return

    bot_id_str = str(bot.id)
    offset = telegram_offsets.get(bot_id_str, 0)

    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=1"
        resp = await client.get(url, timeout=3.0)
        if resp.status_code == 200 and resp.json().get("ok"):
            updates = resp.json().get("result", [])
            for up in updates:
                up_id = up.get("update_id", 0)
                telegram_offsets[bot_id_str] = max(offset, up_id + 1)
                
                msg = up.get("message") or up.get("edited_message")
                if not msg:
                    continue
                    
                chat = msg.get("chat", {})
                chat_id = str(chat.get("id", ""))
                text = msg.get("text", "").strip()
                
                if not chat_id or not text:
                    continue

                allowed_ids = [c.strip() for c in config.get("allowed_chat_ids", "").split(",") if c.strip()]
                
                if not allowed_ids:
                    logger.warning("Ignoring Telegram message for bot %s because no allowed chat IDs are configured", bot.id)
                    continue

                if chat_id in allowed_ids:
                    # Gửi typing action
                    await client.post(f"https://api.telegram.org/bot{token}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
                    
                    # Sinh câu trả lời bằng AI thông minh
                    reply_text = await _generate_ai_reply(text)
                    await client.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": reply_text})
    except Exception as exc:
        logger.debug(f"Telegram polling error for bot {bot.id}: {exc}")


async def process_zalo_bot(client: httpx.AsyncClient, bot: Chatbot, db: Session):
    config = bot.channel_config_jsonb or {}
    token = config.get("bot_token", "").strip()
    if not token or not config.get("is_enabled", False):
        return

    try:
        url = f"https://bot-api.zaloplatforms.com/bot{token}/getUpdates"
        resp = await client.post(url, json={"timeout": 1}, timeout=3.0)
        if resp.status_code == 200:
            res_json = resp.json()
            res = res_json.get("result")
            raw_items = []
            if isinstance(res, dict):
                if res.get("message") or res.get("event_name"):
                    raw_items = [res]
                else:
                    for k in ("updates", "messages", "events", "data"):
                        if isinstance(res.get(k), list):
                            raw_items = res[k]
                            break
            elif isinstance(res, list):
                raw_items = res

            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                msg = item.get("message") if isinstance(item.get("message"), dict) else item
                if not isinstance(msg, dict):
                    continue
                    
                msg_id = str(msg.get("message_id") or msg.get("msg_id") or "")
                if msg_id and msg_id in processed_zalo_msgs:
                    continue
                if msg_id:
                    processed_zalo_msgs.add(msg_id)
                    if len(processed_zalo_msgs) > 5000:
                        processed_zalo_msgs.clear()

                chat_obj = msg.get("chat") or {}
                from_obj = msg.get("from") or item.get("sender") or {}
                chat_id = str(chat_obj.get("id") or from_obj.get("id") or msg.get("chat_id") or "")
                text = str(msg.get("text") or "").strip()
                
                if not chat_id or not text:
                    continue

                allowed_ids = [c.strip() for c in config.get("allowed_chat_ids", "").split(",") if c.strip()]
                
                if not allowed_ids:
                    logger.warning("Ignoring Zalo message for bot %s because no allowed chat IDs are configured", bot.id)
                    continue

                if chat_id in allowed_ids:
                    # Gửi typing indicator
                    await client.post(f"https://bot-api.zaloplatforms.com/bot{token}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
                    
                    # Sinh câu trả lời bằng AI thông minh (DeepSeek/OpenRouter)
                    reply_text = await _generate_ai_reply(text)
                    
                    # Gửi tin nhắn trả lời qua Zalo Bot API
                    send_resp = await client.post(
                        f"https://bot-api.zaloplatforms.com/bot{token}/sendMessage",
                        json={"chat_id": chat_id, "text": reply_text}
                    )
                    logger.info(f"Đã gửi trả lời Zalo cho {chat_id}: status={send_resp.status_code}")
    except Exception as exc:
        logger.debug(f"Zalo polling error for bot {bot.id}: {exc}")


async def channel_worker_loop():
    """
    Vòng lặp chạy ngầm định kỳ kiểm tra tin nhắn mới từ Telegram & Zalo Bots.
    """
    logger.info("Starting Channel Worker loop (Telegram & Zalo polling)...")
    async with httpx.AsyncClient() as client:
        while True:
            db = SessionLocal()
            try:
                bots = db.query(Chatbot).all()
                for bot in bots:
                    if bot.channel == "telegram":
                        await process_telegram_bot(client, bot, db)
                    elif bot.channel == "zalo":
                        await process_zalo_bot(client, bot, db)
            except Exception as e:
                logger.exception(f"Error in channel worker loop: {e}")
            finally:
                db.close()
            await asyncio.sleep(2.0)
