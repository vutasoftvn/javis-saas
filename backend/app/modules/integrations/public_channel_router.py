from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from app.db.session import get_db
from app.modules.integrations.telegram_adapter import parse_telegram_update
from app.modules.integrations.zalo_adapter import parse_zalo_webhook
from app.modules.integrations.n8n_gateway_service import handle_n8n_callback

router = APIRouter()


@router.post("/public/channels/telegram/webhook/{workspace_id}")
async def receive_telegram_webhook(
    workspace_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Tiếp nhận update từ Telegram Bot API Webhook."""
    payload = await request.json()
    parsed = parse_telegram_update(payload)
    return {
        "status": "ok",
        "workspace_id": str(workspace_id),
        "received_update": parsed,
    }


@router.post("/public/channels/zalo/webhook/{workspace_id}")
async def receive_zalo_webhook(
    workspace_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Tiếp nhận event từ Zalo OA Webhook."""
    payload = await request.json()
    parsed = parse_zalo_webhook(payload)
    return {
        "status": "ok",
        "workspace_id": str(workspace_id),
        "received_event": parsed,
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
