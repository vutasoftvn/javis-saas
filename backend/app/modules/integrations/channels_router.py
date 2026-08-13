from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
import httpx

from app.db.session import get_db
from app.db.models import Chatbot, WorkspaceMember, User
from app.core.auth import get_current_user

router = APIRouter()

class TelegramChannelConfig(BaseModel):
    workspace_id: str
    is_enabled: bool
    bot_token: str
    allowed_chat_ids: Optional[str] = ""

class ZaloChannelConfig(BaseModel):
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

@router.get("")
def get_channels_config(
    workspace_id: str = Query(..., description="ID của workspace"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách cấu hình tất cả các kênh (Telegram, Zalo) của workspace.
    """
    get_member(workspace_id, current_user.id, db)
    
    bots = db.query(Chatbot).filter(Chatbot.workspace_id == workspace_id).all()
    
    result = {
        "telegram": {
            "is_enabled": False,
            "bot_token": "",
            "allowed_chat_ids": "",
            "bot_username": "",
            "status": "off",
            "last_error": None
        },
        "zalo": {
            "is_enabled": False,
            "bot_token": "",
            "allowed_chat_ids": "",
            "bot_username": "",
            "status": "off",
            "last_error": None
        }
    }
    
    for bot in bots:
        if bot.channel in result and bot.channel_config_jsonb:
            cfg = bot.channel_config_jsonb
            is_en = cfg.get("is_enabled", False)
            result[bot.channel] = {
                "is_enabled": is_en,
                "bot_token": cfg.get("bot_token", ""),
                "allowed_chat_ids": cfg.get("allowed_chat_ids", ""),
                "bot_username": cfg.get("bot_username", ""),
                "status": "running" if is_en else "off",
                "last_error": cfg.get("last_error")
            }
            
    return result

@router.post("/telegram/save")
async def save_telegram_channel(
    data: TelegramChannelConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lưu và bật/tắt bot Telegram.
    """
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

@router.post("/telegram/test")
async def test_telegram_channel(
    data: ChannelTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Gửi tin nhắn test qua Telegram Bot API.
    """
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
        # Nếu chưa có Chat ID, thử getMe xác thực token
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

@router.post("/zalo/save")
async def save_zalo_channel(
    data: ZaloChannelConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lưu và bật/tắt bot Zalo.
    """
    get_member(data.workspace_id, current_user.id, db)
    
    bot_username = "ZaloBot"
    last_err = None
    
    if data.is_enabled and data.bot_token:
        token = data.bot_token.strip()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(f"https://bot-api.zaloplatforms.com/bot{token}/getMe", json={})
                if resp.status_code == 200 and resp.json().get("ok"):
                    res_data = resp.json().get("result", {})
                    bot_username = res_data.get("display_name") or res_data.get("account_name") or "ZaloBot"
                else:
                    err_desc = resp.json().get("description") if resp.status_code == 200 else f"HTTP {resp.status_code}"
                    last_err = f"Token không hợp lệ: {err_desc}"
        except Exception as exc:
            last_err = f"Không kết nối được Zalo Bot API: {exc}"

    bot = db.query(Chatbot).filter(
        Chatbot.workspace_id == data.workspace_id,
        Chatbot.channel == "zalo"
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
            name=f"Zalo Bot ({bot_username})",
            channel="zalo",
            channel_config_jsonb=config_data
        )
        db.add(bot)
    else:
        bot.channel_config_jsonb = config_data
        bot.name = f"Zalo Bot ({bot_username})"
        
    db.commit()
    db.refresh(bot)
    
    return {
        "status": "success",
        "bot_id": str(bot.id),
        "bot_username": bot_username,
        "is_enabled": data.is_enabled,
        "message": f"Đã lưu cấu hình bot Zalo ({bot_username}) thành công"
    }

@router.post("/zalo/test")
async def test_zalo_channel(
    data: ChannelTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Gửi tin nhắn test qua Zalo Bot Manager API.
    """
    get_member(data.workspace_id, current_user.id, db)
    
    bot = db.query(Chatbot).filter(
        Chatbot.workspace_id == data.workspace_id,
        Chatbot.channel == "zalo"
    ).first()
    
    if not bot or not bot.channel_config_jsonb:
        raise HTTPException(status_code=400, detail="Chưa lưu cấu hình bot Zalo")
        
    config = bot.channel_config_jsonb
    token = config.get("bot_token", "")
    chat_ids_str = config.get("allowed_chat_ids", "")
    
    if not token:
        raise HTTPException(status_code=400, detail="Thiếu Bot Token Zalo")
        
    chat_ids = [c.strip() for c in chat_ids_str.split(",") if c.strip()]
    if not chat_ids:
        # Nếu chưa có Chat ID, tự động gọi getMe để kiểm tra tính hợp lệ của Token Zalo
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"https://bot-api.zaloplatforms.com/bot{token}/getMe", json={})
            if resp.status_code == 200 and resp.json().get("ok"):
                bot_name = resp.json().get("result", {}).get("display_name") or "Bot Zalo"
                return {
                    "status": "success",
                    "sent_count": 0,
                    "message": f"Kích hoạt Zalo Bot '{bot_name}' thành công! Token hợp lệ 100%. Vui lòng mở Zalo nhắn 1 tin cho Bot để ghi nhận Chat ID tự động."
                }
            else:
                err_desc = resp.json().get("description") if resp.status_code == 200 else f"HTTP {resp.status_code}"
                raise HTTPException(
                    status_code=400,
                    detail=f"Zalo Bot Token không hợp lệ ({err_desc}). Vui lòng kiểm tra lại Token Zalo Bot."
                )
        
    success_count = 0
    last_err = ""
    test_msg = "🤖 COSA OS: Tin nhắn kiểm tra kết nối Zalo Bot thành công!"
    
    for cid in chat_ids:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"https://bot-api.zaloplatforms.com/bot{token}/sendMessage",
                    json={"chat_id": cid, "text": test_msg}
                )
                if resp.status_code == 200:
                    res_json = resp.json()
                    if res_json.get("ok") or res_json.get("error") == 0:
                        success_count += 1
                    else:
                        last_err = res_json.get("description") or res_json.get("message") or f"Lỗi Zalo API {res_json}"
                else:
                    last_err = f"Lỗi Zalo HTTP {resp.status_code}"
        except Exception as exc:
            last_err = str(exc)
            
    if success_count == 0:
        raise HTTPException(
            status_code=400,
            detail=f"Zalo từ chối gửi tin: {last_err or 'Không kết nối được Zalo Bot API'}"
        )

    return {
        "status": "success",
        "sent_count": success_count,
        "message": f"Đã gửi tin nhắn thử nghiệm Zalo Bot thành công tới {success_count} Chat ID!"
    }

# --- Chatbots CRUD ---

@router.get("/list")
def list_chatbots(
    workspace_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    get_member(workspace_id, current_user.id, db)
    bots = db.query(Chatbot).filter(Chatbot.workspace_id == workspace_id).all()
    return [
        {
            "id": str(b.id),
            "name": b.name,
            "channel": b.channel,
            "is_enabled": b.channel_config_jsonb.get("is_enabled", False) if b.channel_config_jsonb else False,
            "status": "running" if b.channel_config_jsonb and b.channel_config_jsonb.get("is_enabled") else "off",
            "bot_username": b.channel_config_jsonb.get("bot_username", "") if b.channel_config_jsonb else "",
            "allowed_chat_ids": b.channel_config_jsonb.get("allowed_chat_ids", "") if b.channel_config_jsonb else "",
            "last_error": b.channel_config_jsonb.get("last_error") if b.channel_config_jsonb else None
        }
        for b in bots
    ]
