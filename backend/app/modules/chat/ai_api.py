from fastapi import APIRouter, Depends
from app.modules.chat.model_registry import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    is_provider_configured,
    list_models,
)
from app.db.models import WorkspaceMember
from app.core.auth import get_current_workspace_member

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
