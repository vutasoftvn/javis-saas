from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from db.session import get_db
from core.auth import get_current_workspace_member
from db.models import WorkspaceMember
from integrations.channels.outbox import outbox_processor
from integrations.channels.telegram import telegram_adapter
from integrations.channels.zalo import zalo_adapter
from integrations.workflows import n8n_gateway_service



router = APIRouter()


class TestTelegramRequest(BaseModel):
    bot_token: str = Field(..., description="Telegram Bot Token")


class TestZaloRequest(BaseModel):
    app_id: str = Field(..., description="Zalo App ID")
    secret_key: str = Field(..., description="Zalo Secret Key")
    access_token: Optional[str] = None


class DispatchAutomationRequest(BaseModel):
    automation_key: str = Field(..., description="Mã định danh automation")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Dữ liệu đầu vào")
    webhook_url: Optional[str] = None


@router.get("/workspaces/{workspace_id}/outbox")
def get_outbox(
    workspace_id: int,
    status: Optional[str] = Query(None, description="pending | sent | failed"),
    limit: int = 50,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    items = outbox_processor.list_outbox_items(db, workspace_id, status, limit)
    return {"status": "success", "data": items}


@router.post("/workspaces/{workspace_id}/outbox/{outbox_id}/retry")
def retry_outbox(
    workspace_id: int,
    outbox_id: str,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    try:
        oid = int(outbox_id)
        res = outbox_processor.retry_outbox_item(db, workspace_id, oid)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workspaces/{workspace_id}/outbox/process-batch")
def trigger_process_batch(
    workspace_id: int,
    limit: int = 20,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    res = outbox_processor.process_outbox_batch_sync(db, limit)
    return res


@router.post("/workspaces/{workspace_id}/channels/telegram/test")
async def test_telegram(
    workspace_id: int,
    payload: TestTelegramRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    res = await telegram_adapter.test_telegram_connection(payload.bot_token)
    return res


@router.post("/workspaces/{workspace_id}/channels/zalo/test")
async def test_zalo(
    workspace_id: int,
    payload: TestZaloRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    res = await zalo_adapter.test_zalo_connection(payload.app_id, payload.secret_key, payload.access_token)
    return res


@router.post("/workspaces/{workspace_id}/automations/dispatch")
async def dispatch_automation(
    workspace_id: int,
    payload: DispatchAutomationRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    res = await n8n_gateway_service.dispatch_n8n_workflow(
        db=db,
        workspace_id=workspace_id,
        automation_key=payload.automation_key,
        payload=payload.payload,
        webhook_url=payload.webhook_url,
    )
    return {"status": "success", "data": res}
