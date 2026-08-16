from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from app.db.session import get_db
from app.modules.integrations.channel_pipeline import ChannelPipelineService
from app.modules.integrations.n8n_gateway_service import handle_n8n_callback

router = APIRouter()


@router.post("/public/channels/telegram/webhook/{workspace_id}")
async def receive_telegram_webhook(
    workspace_id: int,
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: Session = Depends(get_db),
):
    """Tiếp nhận update từ Telegram Bot API Webhook qua Channel Pipeline (Verify, Dedupe, Normalize)."""
    payload = await request.json()
    event = ChannelPipelineService.verify_and_normalize_telegram(
        workspace_id=workspace_id,
        payload=payload,
        secret_token=x_telegram_bot_api_secret_token,
    )
    if not event:
        return {
            "status": "ignored_or_duplicate",
            "workspace_id": str(workspace_id),
        }

    return {
        "status": "accepted",
        "workspace_id": str(workspace_id),
        "event_id": event.event_id,
        "channel": event.channel,
        "sender_id": event.sender_id,
        "content": event.content,
        "dedupe_key": event.dedupe_key,
    }


@router.post("/public/channels/zalo/webhook/{workspace_id}")
async def receive_zalo_webhook(
    workspace_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Tiếp nhận event từ Zalo OA Webhook qua Channel Pipeline (Verify, Dedupe, Normalize)."""
    payload = await request.json()
    event = ChannelPipelineService.verify_and_normalize_zalo(
        workspace_id=workspace_id,
        payload=payload,
    )
    if not event:
        return {
            "status": "ignored_or_duplicate",
            "workspace_id": str(workspace_id),
        }

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


@router.post("/public/automations/callback/{run_id}")
async def receive_automation_callback(
    run_id: str,
    request: Request,
    x_cosa_signature: Optional[str] = Header(None, alias="X-COSA-Signature"),
    db: Session = Depends(get_db),
):
    """Tiếp nhận webhook callback từ n8n khi workflow hoàn thành."""
    raw_body = await request.body()
    payload = await request.json()

    try:
        rid = int(run_id)
        res = handle_n8n_callback(
            db=db,
            run_id=rid,
            payload=payload,
            raw_body_bytes=raw_body,
            signature_header=x_cosa_signature or "",
        )
        return res
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
