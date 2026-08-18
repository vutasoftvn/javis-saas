from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Chatbot, WorkspaceMember, User, MCPConnection
from app.core.auth import get_current_user, get_current_workspace_member
from app.integrations.channels.secrets_service import encrypt_for_workspace
from app.integrations.channels.telegram.router import router as telegram_router
from app.integrations.channels.zalo.router import router as zalo_router
from app.integrations.channels.outbox.channel_pipeline import ChannelPipelineService

router = APIRouter()

# Mount sub-channel routers
router.include_router(telegram_router, prefix="/telegram", tags=["telegram-channel"])
router.include_router(zalo_router, prefix="/zalo", tags=["zalo-channel"])

def get_member(workspace_id: str, user_id: str, db: Session) -> WorkspaceMember:
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Tài khoản không thuộc workspace này")
    return member

# --- Overview Channel Status ---
@router.get("")
def get_channels_config(
    workspace_id: str = Query(..., description="ID của workspace"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách cấu hình tất cả các kênh (Telegram, Zalo) của workspace."""
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

# --- Public Webhooks ---
@router.post("/public/telegram/webhook/{workspace_id}")
async def receive_telegram_webhook(
    workspace_id: int,
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: Session = Depends(get_db),
):
    payload = await request.json()
    event = ChannelPipelineService.verify_and_normalize_telegram(
        workspace_id=workspace_id,
        payload=payload,
        secret_token=x_telegram_bot_api_secret_token,
    )
    if not event:
        return {"status": "ignored_or_duplicate", "workspace_id": str(workspace_id)}

    return {
        "status": "accepted",
        "workspace_id": str(workspace_id),
        "event_id": event.event_id,
        "channel": event.channel,
        "sender_id": event.sender_id,
        "content": event.content,
        "dedupe_key": event.dedupe_key,
    }

@router.post("/public/zalo/webhook/{workspace_id}")
async def receive_zalo_webhook(
    workspace_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    payload = await request.json()
    event = ChannelPipelineService.verify_and_normalize_zalo(
        workspace_id=workspace_id,
        payload=payload,
    )
    if not event:
        return {"status": "ignored_or_duplicate", "workspace_id": str(workspace_id)}

    return {
        "status": "accepted",
        "workspace_id": str(workspace_id),
        "event_id": event.event_id,
        "channel": event.channel,
        "event_type": event.event_type,
        "sender_id": event.sender_id,
        "content": event.content,
        "dedupe_key": event.dedupe_key,
    }

# --- MCP Connections ---
class ConnectorCreate(BaseModel):
    name: str
    config_jsonb: dict

@router.get("/connectors")
def list_connectors(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    connectors = db.query(MCPConnection).filter(MCPConnection.workspace_id == workspace_id).all()
    return {
        "connectors": [
            {
                "id": str(c.id),
                "name": c.name,
                "status": c.status,
                "created_at": c.created_at.isoformat()
            } for c in connectors
        ]
    }
