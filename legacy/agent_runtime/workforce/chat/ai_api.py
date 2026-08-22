from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from workforce.chat.model_registry import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    is_provider_configured,
    list_models,
)
from db.models import WorkspaceMember
from core.auth import get_current_workspace_member


router = APIRouter()

@router.get("/models")
def get_models(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member)
):
    models = list_models()
    configured_flags = {m.provider: is_provider_configured(m.provider) for m in models}
    
    # Chỉ lọc và trả về những model có API Key đã được cấu hình (configured == True)
    configured_models = [m for m in models if configured_flags.get(m.provider)]

    ordered = sorted(
        configured_models,
        key=lambda m: (
            not (m.provider == DEFAULT_PROVIDER and m.model == DEFAULT_MODEL),
        ),
    )

    return {
        "models": [
            {
                "provider": m.provider,
                "model": m.model,
                "label": m.label,
                "supports_tools": m.supports_tools,
                "supports_vision": m.supports_vision,
                "context_window": m.context_window,
                "configured": True,
            }
            for m in ordered
        ]
    }


@router.get("/usage")
def get_usage(
    workspace_id: int,
    period: str = "30d",
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: member does not belong to this workspace",
        )
    from platform_core.core.usage_service import get_usage_summary

    return get_usage_summary(db=db, workspace_id=workspace_id, period=period)


from pydantic import BaseModel

class OpenRouterKeyCreate(BaseModel):
    workspace_id: int
    api_key: str

@router.post("/openrouter-key")
def save_openrouter_key(
    body: OpenRouterKeyCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != body.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: member does not belong to this workspace",
        )
    key_str = body.api_key.strip()
    if not key_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API Key không được để trống",
        )

    from integrations.channels.models import WorkspaceSecret
    from integrations.channels.secrets_service import encrypt_for_workspace

    enc_val = encrypt_for_workspace(body.workspace_id, key_str)
    
    ws_secret = (
        db.query(WorkspaceSecret)
        .filter(WorkspaceSecret.workspace_id == body.workspace_id, WorkspaceSecret.key == "openrouter")
        .first()
    )
    if ws_secret:
        ws_secret.encrypted_value = enc_val
    else:
        ws_secret = WorkspaceSecret(
            workspace_id=body.workspace_id,
            key="openrouter",
            encrypted_value=enc_val,
        )
        db.add(ws_secret)
    
    db.commit()
    return {"message": "Đã mã hoá và lưu OpenRouter API Key cho Workspace thành công", "is_custom_workspace_key": True}


@router.delete("/openrouter-key")
def delete_openrouter_key(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: member does not belong to this workspace",
        )

    from integrations.channels.models import WorkspaceSecret

    db.query(WorkspaceSecret).filter(
        WorkspaceSecret.workspace_id == workspace_id,
        WorkspaceSecret.key == "openrouter",
    ).delete()
    db.commit()
    return {"message": "Đã xoá khoá riêng Workspace, quay lại dùng khoá mặc định hệ thống", "is_custom_workspace_key": False}



