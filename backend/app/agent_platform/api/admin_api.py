from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.session import get_db
from app.core.auth import get_current_user
from app.modules.iam.models import User
from app.agent_platform.models import (
    AgentDefinition, ToolDefinition, AgentToolPermission,
    PlatformPromptTemplate, PlatformPromptVersion
)
from app.agent_platform.registry.agent_registry import AgentRegistryService
from app.agent_platform.registry.tool_registry import ToolRegistryService
from app.agent_platform.registry.prompt_registry import PromptRegistryService
from app.agent_platform.routing.router import IntentRouter, IntentDecision
from app.core.snowflake import generate_snowflake_id


router = APIRouter(prefix="/api/v1/agent-platform", tags=["Agent Platform Control Plane"])


# --- Schemas ---

class AgentCreateOrUpdateRequest(BaseModel):
    key: str
    name: str
    description: Optional[str] = None
    agent_type: str = "specialist"
    default_model_profile: str = "reasoning"
    system_prompt_key: str = "default.system"
    risk_level: int = 1
    enabled: bool = True
    config: Dict[str, Any] = {}


class ToolCreateOrUpdateRequest(BaseModel):
    key: str
    name: str
    description: Optional[str] = None
    transport: str = "local"
    risk_level: int = 0
    requires_approval: bool = False
    enabled: bool = True
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    config: Dict[str, Any] = {}


class PermissionUpdateRequest(BaseModel):
    agent_id: int
    tool_id: int
    allow_execute: bool
    requires_approval: bool


class PromptUpdateRequest(BaseModel):
    new_content: str
    change_note: Optional[str] = None


class RouteTestRequest(BaseModel):
    message: str


# --- Agent Endpoints ---

@router.get("/agents")
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AgentRegistryService(db)
    agents = await service.list_agents(workspace_id=current_user.workspace_id)
    if not agents:
        # Tự động seed factory defaults nếu chưa có
        agents = await service.seed_factory_defaults(workspace_id=current_user.workspace_id)
        await db.commit()
    return agents


@router.post("/agents")
async def create_or_update_agent(
    req: AgentCreateOrUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AgentRegistryService(db)
    agent = await service.register_agent(
        key=req.key,
        name=req.name,
        description=req.description,
        agent_type=req.agent_type,
        default_model_profile=req.default_model_profile,
        system_prompt_key=req.system_prompt_key,
        risk_level=req.risk_level,
        workspace_id=current_user.workspace_id,
        config=req.config,
    )
    await db.commit()
    return agent


# --- Tool Endpoints ---

@router.get("/tools")
async def list_tools(
    transport: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ToolRegistryService(db)
    tools = await service.list_tools(workspace_id=current_user.workspace_id, transport=transport)
    if not tools:
        # Tự động seed factory default tools
        tools = await service.seed_factory_defaults(workspace_id=current_user.workspace_id)
        await db.commit()
    return tools


@router.post("/tools")
async def create_or_update_tool(
    req: ToolCreateOrUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ToolRegistryService(db)
    tool = await service.register_tool(
        key=req.key,
        name=req.name,
        description=req.description,
        transport=req.transport,
        risk_level=req.risk_level,
        requires_approval=req.requires_approval,
        input_schema=req.input_schema,
        output_schema=req.output_schema,
        config=req.config,
        workspace_id=current_user.workspace_id,
    )
    await db.commit()
    return tool


# --- Permission Matrix Endpoints ---

@router.get("/permissions")
async def get_permissions(
    agent_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(AgentToolPermission)
    filters = []
    if current_user.workspace_id is not None:
        filters.append(AgentToolPermission.workspace_id == current_user.workspace_id)
    if agent_id is not None:
        filters.append(AgentToolPermission.agent_id == agent_id)
    if filters:
        stmt = stmt.where(and_(*filters))
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.post("/permissions")
async def set_permission(
    req: PermissionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(AgentToolPermission).where(
        and_(
            AgentToolPermission.agent_id == req.agent_id,
            AgentToolPermission.tool_id == req.tool_id,
            AgentToolPermission.workspace_id == current_user.workspace_id,
        )
    )
    res = await db.execute(stmt)
    perm = res.scalars().first()

    if not perm:
        perm = AgentToolPermission(
            id=generate_snowflake_id(),
            workspace_id=current_user.workspace_id,
            agent_id=req.agent_id,
            tool_id=req.tool_id,
            allow_execute=req.allow_execute,
            requires_approval=req.requires_approval,
        )
        db.add(perm)
    else:
        perm.allow_execute = req.allow_execute
        perm.requires_approval = req.requires_approval

    await db.commit()
    return perm


# --- Prompt Registry Endpoints ---

@router.get("/prompts/{key}")
async def get_prompt(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PromptRegistryService(db)
    content = await service.get_prompt_content(key, current_user.workspace_id)
    tmpl = await service.get_prompt_template(key, current_user.workspace_id)
    return {
        "key": key,
        "content": content,
        "version": tmpl.current_version if tmpl else 1,
        "default_content": tmpl.default_content if tmpl else content,
    }


@router.put("/prompts/{key}")
async def update_prompt(
    key: str,
    req: PromptUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PromptRegistryService(db)
    tmpl = await service.update_prompt_content(
        key=key,
        new_content=req.new_content,
        workspace_id=current_user.workspace_id,
        updated_by=current_user.id,
        change_note=req.change_note,
    )
    await db.commit()
    return tmpl


@router.post("/prompts/{key}/restore-default")
async def restore_default_prompt(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PromptRegistryService(db)
    tmpl = await service.restore_default(
        key=key,
        workspace_id=current_user.workspace_id,
        restored_by=current_user.id,
    )
    if not tmpl:
        raise HTTPException(status_code=404, detail="No factory default prompt found for this key")
    await db.commit()
    return tmpl


# --- Router Diagnostic & Test Endpoint ---

@router.post("/routing/test")
async def test_route_message(
    req: RouteTestRequest,
    current_user: User = Depends(get_current_user),
):
    decision: IntentDecision = await IntentRouter.route_message(req.message)
    return decision
