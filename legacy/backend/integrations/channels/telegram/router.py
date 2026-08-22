from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import httpx

from db.session import get_db
from db.models import Chatbot, WorkspaceMember, User
from core.auth import get_current_user

router = APIRouter()

class TelegramChannelConfig(BaseModel):
    workspace_id: str
    is_enabled: bool
    bot_token: str
    allowed_chat_ids: Optional[str] = ""

class ChannelTestRequest(BaseModel):
    workspace_id: str

def get_member(workspace_id: str, user_id: str, db: Session) -> WorkspaceMember:
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Tài khoản không thuộc workspace này")
    return member

@router.post("/save")
async def save_telegram_channel(
    data: TelegramChannelConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    get_member(data.workspace_id, current_user.id, db)
    bot_username = ""
    last_err = None
    
    if data.is_enabled and data.bot_token:
        token = data.bot_token.strip()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
                if resp.status_code == 200 and resp.json().get("ok"):
                    res_data = resp.json().get("result", {})
                    bot_username = res_data.get("username", "")
                else:
                    last_err = f"Token không hợp lệ: {resp.text}"
        except Exception as exc:
            last_err = f"Không kết nối được Telegram API: {exc}"
            
    bot = db.query(Chatbot).filter(
        Chatbot.workspace_id == data.workspace_id,
        Chatbot.channel == "telegram"
    ).first()
    
    config_data = {
        "is_enabled": data.is_enabled,
        "bot_token": data.bot_token.strip() if data.bot_token else "",
        "allowed_chat_ids": data.allowed_chat_ids.strip() if data.allowed_chat_ids else "",
        "bot_username": bot_username,
        "last_error": last_err
    }
    
    if not bot:
        bot = Chatbot(
            workspace_id=data.workspace_id,
            name=f"Telegram Bot (@{bot_username})" if bot_username else "Telegram Bot",
            channel="telegram",
            channel_config_jsonb=config_data
        )
        db.add(bot)
    else:
        bot.channel_config_jsonb = config_data
        if bot_username:
            bot.name = f"Telegram Bot (@{bot_username})"
            
    db.commit()
    db.refresh(bot)
    
    return {
        "status": "success",
        "bot_id": str(bot.id),
        "bot_username": bot_username,
        "is_enabled": data.is_enabled,
        "message": "Đã lưu cấu hình bot Telegram thành công"
    }

@router.post("/test")
async def test_telegram_channel(
    data: ChannelTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    get_member(data.workspace_id, current_user.id, db)
    bot = db.query(Chatbot).filter(
        Chatbot.workspace_id == data.workspace_id,
        Chatbot.channel == "telegram"
    ).first()
    
    if not bot or not bot.channel_config_jsonb:
        raise HTTPException(status_code=400, detail="Chưa lưu cấu hình bot Telegram")
        
    config = bot.channel_config_jsonb
    token = config.get("bot_token", "")
    chat_ids_str = config.get("allowed_chat_ids", "")
    
    if not token:
        raise HTTPException(status_code=400, detail="Thiếu Bot Token Telegram")
        
    chat_ids = [c.strip() for c in chat_ids_str.split(",") if c.strip()]
    if not chat_ids:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            if resp.status_code == 200 and resp.json().get("ok"):
                username = resp.json().get("result", {}).get("username", "")
                return {
                    "status": "success",
                    "sent_count": 0,
                    "message": f"Kích hoạt Telegram Bot @{username} thành công! Hãy nhập Chat ID được phép trước khi bot phản hồi tin nhắn."
                }
            else:
                raise HTTPException(status_code=400, detail="Token Telegram không hợp lệ.")
        
    success_count = 0
    last_err = ""
    test_msg = "🤖 COSA OS: Tin nhắn kiểm tra kết nối Telegram Bot thành công!"
    
    for cid in chat_ids:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": cid, "text": test_msg}
                )
                if resp.status_code == 200 and resp.json().get("ok"):
                    success_count += 1
                else:
                    last_err = resp.json().get("description") or resp.text
        except Exception as exc:
            last_err = str(exc)
            
    if success_count == 0:
        raise HTTPException(
            status_code=400,
            detail=f"Telegram từ chối gửi tin: {last_err or 'Không kết nối được Telegram Bot API'}"
        )

    return {
        "status": "success",
        "sent_count": success_count,
        "message": f"Đã gửi tin nhắn thử nghiệm Telegram thành công tới {success_count} Chat ID!"
    }
