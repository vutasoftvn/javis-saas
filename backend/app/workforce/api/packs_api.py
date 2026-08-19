"""Workforce Packs & Domain Registry API Router (F4 Specification).

Cung cấp API quản lý danh sách 5 Core Domains và bật/tắt các Optional Packs (Operations, HR, Support)
dành cho Workspace Settings và AI Workforce Store.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.auth import get_current_user
from app.platform.auth.models import User
from app.workforce.api.admin_api import get_workforce_db
from app.workforce.models import AgentDefinition
from app.workforce.registry.agent_registry import AgentRegistryService
from app.workforce.schemas.agent_category_schemas import AgentCategoryEnum


router = APIRouter(prefix="/workforce/packs", tags=["Workforce Packs"])


class WorkforcePackItem(BaseModel):
    key: str
    name: str
    role_title: Optional[str] = None
    department: Optional[str] = None
    category: str = Field(..., description="ORCHESTRATOR | DOMAIN | OPTIONAL_DOMAIN | LEGACY")
    is_core: bool
    is_active: bool
    description: Optional[str] = None
    tools_count: int = 0


class TogglePackRequest(BaseModel):
    is_active: bool = Field(..., description="Trạng thái kích hoạt gói mở rộng")
    workspace_id: Optional[int] = None


class TogglePackResponse(BaseModel):
    key: str
    is_active: bool
    message: str


@router.get("", response_model=List[WorkforcePackItem])
async def list_workforce_packs(
    workspace_id: Optional[int] = Query(None),
    db=Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách toàn bộ các 5 Core Domains và Optional Packs."""
    stmt = select(AgentDefinition)
    if workspace_id is not None:
        stmt = stmt.where(AgentDefinition.workspace_id == workspace_id)
    else:
        stmt = stmt.where(AgentDefinition.workspace_id.is_(None))

    res = await db.execute(stmt)
    agents = list(res.scalars().all())

    # Nếu chưa có trong DB, nạp trực tiếp từ DEFAULT_AGENT_MANIFESTS
    if not agents:
        from app.workforce.registry.defaults import DEFAULT_AGENT_MANIFESTS
        items: List[WorkforcePackItem] = []
        for m in DEFAULT_AGENT_MANIFESTS:
            cat = m.get("category", "DOMAIN")
            items.append(
                WorkforcePackItem(
                    key=m["key"],
                    name=m["name"],
                    role_title=m.get("role_title"),
                    department=m.get("department"),
                    category=cat,
                    is_core=(cat == "DOMAIN" or cat == "ORCHESTRATOR"),
                    is_active=bool(m.get("is_default_active", True)),
                    description=m.get("description"),
                    tools_count=len(m.get("default_tool_permissions", []) or []),
                )
            )
        return items

    items: List[WorkforcePackItem] = []
    for agent in agents:
        category = getattr(agent, "category", "DOMAIN") or "DOMAIN"
        is_core = (category == "DOMAIN") or (category == "ORCHESTRATOR")
        is_active = getattr(agent, "is_default_active", True)
        
        items.append(
            WorkforcePackItem(
                key=agent.key,
                name=agent.name,
                role_title=agent.role_title,
                department=agent.department,
                category=category,
                is_core=is_core,
                is_active=bool(is_active),
                description=agent.description,
                tools_count=len(getattr(agent, "tools", []) or []),
            )
        )

    return items


@router.post("/{pack_key}/toggle", response_model=TogglePackResponse)
async def toggle_optional_pack(
    pack_key: str,
    req: TogglePackRequest,
    db=Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    """Bật hoặc tắt một Optional Pack (HR, Operations, Customer Support...)."""
    stmt = select(AgentDefinition).where(AgentDefinition.key == pack_key)
    if req.workspace_id is not None:
        stmt = stmt.where(AgentDefinition.workspace_id == req.workspace_id)
    
    res = await db.execute(stmt)
    agent = res.scalars().first()

    if not agent:
        # Nếu chưa có agent theo workspace, tìm bản ghi gốc
        stmt_root = select(AgentDefinition).where(AgentDefinition.key == pack_key)
        res_root = await db.execute(stmt_root)
        agent = res_root.scalars().first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pack or Agent with key '{pack_key}' not found",
        )

    # Core Domains không được phép tắt
    category = getattr(agent, "category", "DOMAIN")
    if category == AgentCategoryEnum.ORCHESTRATOR.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable central COSA Co-Founder orchestrator",
        )

    agent.is_default_active = req.is_active
    await db.flush()

    action_text = "kích hoạt" if req.is_active else "vô hiệu hóa"
    return TogglePackResponse(
        key=pack_key,
        is_active=req.is_active,
        message=f"Đã {action_text} gói '{agent.name}' thành công cho Workspace.",
    )
