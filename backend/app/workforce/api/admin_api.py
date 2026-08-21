from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.db.session import get_db
from app.core.auth import get_current_user
from app.platform.auth.models import User
from app.workforce.models import (
    AgentDefinition, AgentHierarchy, ToolDefinition, AgentToolPermission,
    PlatformPromptTemplate, PlatformPromptVersion, LegacyPlatformAgentRun, AgentStep,
    ApprovalRequest, AgentBudget, CostLedger, UnifiedPermission
)
from app.workforce.registry.agent_registry import AgentRegistryService
from app.workforce.registry.tool_registry import ToolRegistryService
from app.workforce.registry.prompt_registry import PromptRegistryService
from app.workforce.adapters.base import ExecutionPayload, Message, ModelRole
from app.workforce.adapters.factory import RuntimeAdapterFactory
from app.workforce.dispatcher.task_dispatcher import AgentTaskDispatcher
from app.workforce.dispatcher.runner import AgentRunnerService
from app.workforce.governance.permission_engine import UnifiedPermissionEngine
from app.workforce.governance.approval_service import ApprovalInboxService
from app.workforce.governance.budget_service import BudgetingEngine, BudgetExceededError
from app.workforce.governance.cost_ledger_service import CostLedgerService
from app.workforce.routing.router import IntentRouter, IntentDecision
from app.core.snowflake import generate_snowflake_id


class AsyncSessionAdapter:
    """Adapter to allow sync SQLAlchemy session to be seamlessly used with async/await workforce services."""
    def __init__(self, session):
        self._session = session

    async def execute(self, *args, **kwargs):
        return self._session.execute(*args, **kwargs)

    async def flush(self, *args, **kwargs):
        return self._session.flush(*args, **kwargs)

    async def commit(self, *args, **kwargs):
        return self._session.commit(*args, **kwargs)

    async def rollback(self, *args, **kwargs):
        return self._session.rollback(*args, **kwargs)

    def add(self, *args, **kwargs):
        return self._session.add(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._session.delete(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._session, name)


def get_workforce_db(db=Depends(get_db)):
    return AsyncSessionAdapter(db)


router = APIRouter()


# --- Schemas ---

class AgentCreateOrUpdateRequest(BaseModel):
    key: str
    name: str
    role_title: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    agent_type: str = "specialist"
    default_model_profile: str = "reasoning"
    system_prompt_key: str = "default.system"
    profile_slug: Optional[str] = None
    risk_level: int = 1
    status: str = "idle"
    enabled: bool = True
    config: Dict[str, Any] = {}
    capabilities: Dict[str, Any] = {}
    model_config: Dict[str, Any] = {}


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


class UnifiedPermissionGrantRequest(BaseModel):
    principal_type: str  # 'USER' | 'AGENT'
    principal_id: int
    resource_type: str   # 'TOOL' | 'DATA' | 'MODULE' | 'BUDGET'
    resource_key: str
    action: str = "EXECUTE"
    is_allowed: bool = True
    requires_approval: bool = False


class PromptUpdateRequest(BaseModel):
    new_content: str
    change_note: Optional[str] = None


class RouteTestRequest(BaseModel):
    message: str


class AgentTestRunRequest(BaseModel):
    prompt: str
    system_prompt_override: Optional[str] = None
    model_override: Optional[str] = None
    temperature: float = 0.2


class TaskDispatchRequest(BaseModel):
    agent_key: Optional[str] = None
    extra_context: Optional[Dict[str, Any]] = None
    bypass_approval_check: bool = False


class ApprovalActionRequest(BaseModel):
    comment: Optional[str] = None


class BudgetSetRequest(BaseModel):
    agent_key: str
    limit_usd: float
    cycle_type: str = "12_WEEK_YEAR"


class AgentCloneRequest(BaseModel):
    new_name: str
    new_key: Optional[str] = None


class AgentToolsBatchUpdateRequest(BaseModel):
    tool_keys: List[str]


class WebhookToolCreateRequest(BaseModel):
    key: str
    name: str
    description: Optional[str] = None
    webhook_url: str
    http_method: str = "POST"
    headers: Optional[Dict[str, str]] = None
    payload_template: Optional[Dict[str, Any]] = None
    risk_level: int = 1
    requires_approval: bool = False


# --- Agent Registry & Org Chart Endpoints ---

@router.get("/agents")
async def list_agents(
    department: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.registry.defaults import DEFAULT_AGENT_MANIFESTS
    service = AgentRegistryService(db)
    agents = await service.list_agents(workspace_id=current_user.workspace_id, department=department)
    if not agents:
        agents = await service.seed_factory_defaults(workspace_id=current_user.workspace_id)
        await db.commit()

    manifest_map = {m["key"]: m for m in DEFAULT_AGENT_MANIFESTS}
    system_keys = set(manifest_map.keys())

    # Lấy permission tool cho từng agent
    res_list = []
    for a in agents:
        is_system = (a.key in system_keys) and (not a.config_jsonb.get("cloned_from"))
        default_tools = manifest_map.get(a.key, {}).get("tools", [])
        custom_tools = a.config_jsonb.get("custom_tools", [])
        tools = list(set(default_tools + custom_tools))
        
        res_list.append({
            "id": a.id,
            "workspace_id": a.workspace_id,
            "key": a.key,
            "name": a.name,
            "role_title": a.role_title,
            "department": a.department,
            "description": a.description,
            "agent_type": a.agent_type,
            "default_model_profile": a.default_model_profile,
            "system_prompt_key": a.system_prompt_key,
            "risk_level": a.risk_level,
            "profile_slug": a.profile_slug,
            "status": a.status,
            "enabled": a.enabled,
            "is_system": is_system,
            "tools": tools,
            "skills": a.config_jsonb.get("skills", []),
            "config": a.config_jsonb,
            "capabilities": a.capabilities_jsonb,
            "model_config": a.model_config_jsonb,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        })
    return res_list


@router.get("/org-chart")
async def get_org_chart(
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    service = AgentRegistryService(db)
    org_chart = await service.get_org_chart(workspace_id=current_user.workspace_id)
    if not org_chart:
        await service.seed_factory_defaults(workspace_id=current_user.workspace_id)
        await db.commit()
        org_chart = await service.get_org_chart(workspace_id=current_user.workspace_id)
    return org_chart


@router.post("/agents")
async def create_or_update_agent(
    req: AgentCreateOrUpdateRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    service = AgentRegistryService(db)
    agent = await service.register_agent(
        key=req.key,
        name=req.name,
        role_title=req.role_title,
        department=req.department,
        description=req.description,
        agent_type=req.agent_type,
        default_model_profile=req.default_model_profile,
        system_prompt_key=req.system_prompt_key,
        profile_slug=req.profile_slug,
        risk_level=req.risk_level,
        status=req.status,
        workspace_id=current_user.workspace_id,
        config=req.config,
        capabilities=req.capabilities,
        model_config=req.model_config,
    )
    await db.commit()
    return agent


@router.delete("/agents/{agent_id_or_key}")
async def delete_agent(
    agent_id_or_key: str,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    service = AgentRegistryService(db)
    try:
        await service.delete_agent(agent_id_or_key, workspace_id=current_user.workspace_id)
        await db.commit()
        return {"status": "deleted", "key_or_id": agent_id_or_key}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/agents/{key}/clone")
async def clone_agent(
    key: str,
    req: AgentCloneRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    service = AgentRegistryService(db)
    new_key = req.new_key or f"{key}_custom_{uuid.uuid4().hex[:6]}"
    try:
        cloned = await service.clone_agent(
            source_key=key,
            new_key=new_key,
            new_name=req.new_name,
            workspace_id=current_user.workspace_id,
        )
        await db.commit()
        return cloned
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/agents/{key}/tools/batch-update")
async def batch_update_agent_tools(
    key: str,
    req: AgentToolsBatchUpdateRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    service = AgentRegistryService(db)
    agent = await service.get_agent_by_key(key, current_user.workspace_id)
    if not agent:
        agent = await service.get_agent_by_key(key, None)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{key}' không tồn tại")

    cfg = dict(agent.config_jsonb or {})
    cfg["custom_tools"] = req.tool_keys
    agent.config_jsonb = cfg
    await db.commit()
    return {"status": "updated", "agent_key": key, "tools": req.tool_keys}


@router.post("/tools/webhook")
async def create_webhook_tool(
    req: WebhookToolCreateRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    tool_service = ToolRegistryService(db)
    tool = await tool_service.register_tool(
        key=req.key,
        name=req.name,
        description=req.description or f"Gọi Webhook ngoài {req.webhook_url}",
        transport="api",
        risk_level=req.risk_level,
        requires_approval=req.requires_approval,
        workspace_id=current_user.workspace_id,
        config={
            "webhook_url": req.webhook_url,
            "method": req.http_method,
            "headers": req.headers or {},
            "payload_template": req.payload_template or {},
        }
    )
    await db.commit()
    return tool


@router.post("/agents/{key}/test-run")
async def test_run_agent(
    key: str,
    req: AgentTestRunRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    service = AgentRegistryService(db)
    agent = await service.get_agent_by_key(key, current_user.workspace_id)
    if not agent:
        agent = await service.get_agent_by_key(key, None)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{key}' not found")

    prompt_service = PromptRegistryService(db)
    system_prompt = req.system_prompt_override or await prompt_service.get_prompt_content(agent.system_prompt_key, current_user.workspace_id)

    payload = ExecutionPayload(
        trace_id=f"test_{uuid.uuid4().hex[:16]}",
        agent_key=agent.key,
        model_name=req.model_override or RuntimeAdapterFactory.resolve_model_name(agent.default_model_profile),
        messages=[
            Message(role=ModelRole.SYSTEM, content=system_prompt or "You are a helpful assistant."),
            Message(role=ModelRole.USER, content=req.prompt),
        ],
        temperature=req.temperature,
    )

    runner = AgentRunnerService(db)
    result = await runner.execute_run(
        payload=payload,
        agent=agent,
        workspace_id=current_user.workspace_id,
    )
    await db.commit()

    return {
        "agent_key": agent.key,
        "trace_id": payload.trace_id,
        "content": result.content,
        "usage": {
            "prompt_tokens": result.usage.prompt_tokens,
            "completion_tokens": result.usage.completion_tokens,
            "total_tokens": result.usage.total_tokens,
            "cost_usd": result.usage.cost_usd,
        },
        "latency_ms": result.latency_ms,
        "finish_reason": result.finish_reason,
    }


# --- Task Dispatcher Endpoint ---

@router.post("/tasks/{task_id}/dispatch")
async def dispatch_task_to_agent(
    task_id: int,
    req: TaskDispatchRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    dispatcher = AgentTaskDispatcher(db)
    try:
        res = await dispatcher.dispatch_task(
            task_id=task_id,
            agent_key=req.agent_key,
            extra_context=req.extra_context,
            bypass_approval_check=req.bypass_approval_check,
        )
        await db.commit()
        return res
    except BudgetExceededError as e:
        await db.rollback()
        raise HTTPException(status_code=402, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")


# --- Governance: Human Approval Inbox Endpoints ---

@router.get("/approvals")
async def list_pending_approvals(
    required_role: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    service = ApprovalInboxService(db)
    return await service.list_pending_requests(
        workspace_id=current_user.workspace_id,
        required_role=required_role,
    )


@router.post("/approvals/{request_id}/approve")
async def approve_request(
    request_id: int,
    req: ApprovalActionRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    service = ApprovalInboxService(db)
    try:
        approval = await service.approve(
            request_id=request_id,
            approver_user_id=current_user.id,
            comment=req.comment,
        )
        # Nếu phiếu gắn với Task -> resume thực thi task
        if approval.task_id:
            dispatcher = AgentTaskDispatcher(db)
            await dispatcher.dispatch_task(
                task_id=approval.task_id,
                agent_key=approval.requester_agent_key,
                bypass_approval_check=True,
            )
        await db.commit()
        return {"status": "approved", "approval_id": approval.id, "task_id": approval.task_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/approvals/{request_id}/reject")
async def reject_request(
    request_id: int,
    req: ApprovalActionRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    service = ApprovalInboxService(db)
    try:
        approval = await service.reject(
            request_id=request_id,
            approver_user_id=current_user.id,
            reason=req.comment or "Rejected by user",
        )
        await db.commit()
        return {"status": "rejected", "approval_id": approval.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/approvals/{request_id}/request-revision")
async def request_revision_approval(
    request_id: int,
    req: ApprovalActionRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    if not req.comment:
        raise HTTPException(status_code=400, detail="Feedback is required when requesting revision")
    service = ApprovalInboxService(db)
    try:
        approval = await service.request_revision(
            request_id=request_id,
            approver_user_id=current_user.id,
            feedback=req.comment,
        )
        await db.commit()
        return {"status": "revision_requested", "approval_id": approval.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Governance: Budget & Cost Ledger Endpoints ---

@router.get("/budgets")
async def list_agent_budgets(
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(AgentBudget)
    if current_user.workspace_id is not None:
        stmt = stmt.where(AgentBudget.workspace_id == current_user.workspace_id)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.post("/budgets")
async def set_agent_budget(
    req: BudgetSetRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    service = BudgetingEngine(db)
    budget = await service.set_budget_limit(
        agent_key=req.agent_key,
        limit_usd=req.limit_usd,
        workspace_id=current_user.workspace_id,
        cycle_type=req.cycle_type,
    )
    await db.commit()
    return budget


@router.get("/cost-ledger")
async def get_cost_ledger_summary(
    billing_cycle: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    service = CostLedgerService(db)
    summary = await service.get_cost_summary(
        workspace_id=current_user.workspace_id,
        billing_cycle=billing_cycle,
    )
    recent = await service.list_recent_entries(
        workspace_id=current_user.workspace_id,
        limit=20,
    )
    return {
        "summary": summary,
        "recent_entries": recent,
    }


# --- Unified Permissions Endpoint ---

@router.post("/unified-permissions/grant")
async def grant_unified_permission(
    req: UnifiedPermissionGrantRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    engine = UnifiedPermissionEngine(db)
    perm = await engine.grant_permission(
        principal_type=req.principal_type,
        principal_id=req.principal_id,
        resource_type=req.resource_type,
        resource_key=req.resource_key,
        action=req.action,
        is_allowed=req.is_allowed,
        requires_approval=req.requires_approval,
        workspace_id=current_user.workspace_id,
    )
    await db.commit()
    return perm


# --- Observability & Audit Runs Endpoints ---

@router.get("/runs")
async def list_agent_runs(
    agent_key: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(LegacyPlatformAgentRun).order_by(desc(LegacyPlatformAgentRun.started_at))
    filters = []
    if current_user.workspace_id is not None:
        filters.append(LegacyPlatformAgentRun.workspace_id == current_user.workspace_id)
    if agent_key:
        filters.append(LegacyPlatformAgentRun.agent_key == agent_key)
    if status:
        filters.append(LegacyPlatformAgentRun.status == status)
    if filters:
        stmt = stmt.where(and_(*filters))
    stmt = stmt.offset(offset).limit(limit)

    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/runs/{run_id}")
async def get_agent_run_detail(
    run_id: int,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(LegacyPlatformAgentRun).where(LegacyPlatformAgentRun.id == run_id)
    if current_user.workspace_id is not None:
        stmt = stmt.where(LegacyPlatformAgentRun.workspace_id == current_user.workspace_id)
    res = await db.execute(stmt)
    run_record = res.scalars().first()
    if not run_record:
        raise HTTPException(status_code=404, detail="Agent run record not found")

    steps_stmt = select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.created_at)
    steps_res = await db.execute(steps_stmt)
    steps = list(steps_res.scalars().all())

    return {
        "run": run_record,
        "steps": steps,
    }


# --- Tool Registry Endpoints ---

@router.get("/tools")
async def list_tools(
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    service = ToolRegistryService(db)
    tools = await service.list_tools(workspace_id=current_user.workspace_id)
    if not tools:
        tools = await service.seed_factory_defaults(workspace_id=current_user.workspace_id)
        await db.commit()
    return tools


@router.post("/tools")
async def create_or_update_tool(
    req: ToolCreateOrUpdateRequest,
    db: AsyncSession = Depends(get_workforce_db),
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
        workspace_id=current_user.workspace_id,
        input_schema=req.input_schema,
        output_schema=req.output_schema,
        config=req.config,
    )
    await db.commit()
    return tool


# --- Prompt Registry Endpoints ---

@router.get("/prompts/{key}")
async def get_prompt(
    key: str,
    db: AsyncSession = Depends(get_workforce_db),
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
    db: AsyncSession = Depends(get_workforce_db),
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


# --- Phase C: Prompt Diff & Versions ---

@router.get("/prompts/{key}/diff")
async def get_prompt_diff(
    key: str,
    target_version: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.skills.versioning import SkillVersioningService
    service = SkillVersioningService(db)
    try:
        return await service.get_prompt_diff(
            key=key,
            workspace_id=current_user.workspace_id,
            target_version=target_version,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/prompts/{key}/versions")
async def list_prompt_versions(
    key: str,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    service = PromptRegistryService(db)
    tmpl = await service.get_prompt_template(key, current_user.workspace_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    versions = await service.list_versions(tmpl.id)
    return versions


# --- Phase C: Skill Versions & Reset Default ---

@router.get("/skills/{key}/versions")
async def list_skill_versions(
    key: str,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.skills.skill_registry import SkillRegistryService
    from app.workforce.skills.versioning import SkillVersioningService
    reg_service = SkillRegistryService(db)
    tool = await reg_service.get_tool(key, current_user.workspace_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Skill/Tool '{key}' not found")
    
    ver_service = SkillVersioningService(db)
    return await ver_service.get_tool_versions(tool.id)


@router.post("/skills/{key}/restore-default")
async def restore_default_skill(
    key: str,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.skills.versioning import SkillVersioningService
    service = SkillVersioningService(db)
    try:
        tool = await service.reset_tool_to_default(
            key=key,
            workspace_id=current_user.workspace_id,
            updated_by=current_user.id,
        )
        await db.commit()
        return tool
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))



@router.get("/skills/physical")
async def list_physical_skills(
    department: Optional[str] = None,
    task_context: Optional[str] = None,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách các file SKILL.md vật lý chuẩn hóa (có thể lọc theo department hoặc task on-demand)."""
    from app.workforce.skills.skill_loader import DynamicSkillLoader
    loader = DynamicSkillLoader(db)
    if task_context:
        skills = loader.load_relevant_skills_for_task(task_context, department=department)
    else:
        skills = loader.scan_physical_skills()
        if department and department != "All":
            skills = [s for s in skills if s.department.lower() == department.lower()]

    return [
        {
            "id": s.skill_id,
            "name": s.name,
            "department": s.department,
            "version": s.version,
            "description": s.description,
            "risk_level": s.risk_level,
            "required_tools": s.required_tools,
            "file_path": s.file_path,
            "content_hash": s.content_hash,
            "content_markdown": s.content_markdown,
        }
        for s in skills
    ]


# --- Phase D: Automation & Orchestration (Heartbeats & Routines) ---

@router.get("/heartbeats")
async def list_agent_heartbeats(
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.automation.heartbeat_monitor import HeartbeatMonitorService
    service = HeartbeatMonitorService(db)
    return await service.list_heartbeats(workspace_id=current_user.workspace_id)


@router.post("/heartbeats/check-stalled")
async def check_and_recover_stalled_runs(
    timeout_minutes: int = Query(10, ge=1, le=120),
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.automation.heartbeat_monitor import HeartbeatMonitorService
    service = HeartbeatMonitorService(db)
    recovered = await service.check_and_recover_stalled_runs(
        stalled_timeout_minutes=timeout_minutes,
        workspace_id=current_user.workspace_id,
    )
    await db.commit()
    return {"recovered_count": len(recovered), "recovered_runs": recovered}


@router.get("/routines")
async def list_agent_routines(
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.automation.routine_service import RoutineService
    service = RoutineService(db)
    routines = await service.list_routines(workspace_id=current_user.workspace_id)
    await db.commit()
    return routines


@router.post("/routines/{key}/trigger")
async def trigger_agent_routine(
    key: str,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.automation.routine_service import RoutineService
    service = RoutineService(db)
    try:
        result = await service.trigger_routine(
            key=key,
            workspace_id=current_user.workspace_id,
        )
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Routine execution error: {str(e)}")


# --- Phase E: Work Product Contract & Decision Records ---

class WorkProductReviewRequest(BaseModel):
    feedback: Optional[str] = None


class DecisionRecordCreateRequest(BaseModel):
    title: str
    context_summary: str
    decision_content: str
    consequences: Optional[str] = None
    alternatives_considered: Optional[str] = None
    author_agent_key: str = "founder_copilot"
    work_product_id: Optional[int] = None
    task_id: Optional[int] = None


@router.get("/work-products")
async def list_work_products(
    task_id: Optional[int] = Query(None),
    agent_key: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.work_product.work_product_service import WorkProductService
    service = WorkProductService(db)
    return await service.list_work_products(
        workspace_id=current_user.workspace_id,
        task_id=task_id,
        agent_key=agent_key,
        status=status,
    )


@router.get("/work-products/{product_id}")
async def get_work_product_detail(
    product_id: int,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.work_product.work_product_service import WorkProductService
    service = WorkProductService(db)
    wp = await service.get_work_product(product_id)
    if not wp:
        raise HTTPException(status_code=404, detail="WorkProduct not found")
    return wp


@router.post("/work-products/{product_id}/accept")
async def accept_work_product(
    product_id: int,
    req: WorkProductReviewRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.work_product.work_product_service import WorkProductService
    service = WorkProductService(db)
    try:
        wp = await service.accept_work_product(
            product_id=product_id,
            reviewed_by=current_user.id,
            feedback=req.feedback,
        )
        await db.commit()
        return wp
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/work-products/{product_id}/revise")
async def request_work_product_revision(
    product_id: int,
    req: WorkProductReviewRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.work_product.work_product_service import WorkProductService
    if not req.feedback:
        raise HTTPException(status_code=400, detail="Feedback is required when requesting revision")
    service = WorkProductService(db)
    try:
        wp = await service.request_revision(
            product_id=product_id,
            reviewed_by=current_user.id,
            feedback=req.feedback,
        )
        await db.commit()
        return wp
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/work-products/{product_id}/reject")
async def reject_work_product(
    product_id: int,
    req: WorkProductReviewRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    """G3 Phase 1E: WorkProduct.status already listed REJECTED as a valid
    value, but nothing ever set it - `request_revision` (asks for a redo) was
    the only rejection-shaped action wired up. This is the real reject
    (stop, don't redo)."""
    from app.workforce.work_product.work_product_service import WorkProductService
    if not req.feedback:
        raise HTTPException(status_code=400, detail="Feedback is required when rejecting")
    service = WorkProductService(db)
    try:
        wp = await service.reject_work_product(
            product_id=product_id,
            reviewed_by=current_user.id,
            feedback=req.feedback,
        )
        await db.commit()
        return wp
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/decisions")
async def list_decision_records(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.work_product.decision_service import DecisionRecordService
    service = DecisionRecordService(db)
    return await service.list_decisions(
        workspace_id=current_user.workspace_id,
        status=status,
    )


@router.post("/decisions")
async def create_decision_record(
    req: DecisionRecordCreateRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.work_product.decision_service import DecisionRecordService
    service = DecisionRecordService(db)
    dr = await service.create_decision_record(
        title=req.title,
        context_summary=req.context_summary,
        decision_content=req.decision_content,
        consequences=req.consequences,
        alternatives_considered=req.alternatives_considered,
        author_agent_key=req.author_agent_key,
        work_product_id=req.work_product_id,
        task_id=req.task_id,
        workspace_id=current_user.workspace_id,
    )
    await db.commit()
    return dr


@router.post("/decisions/{decision_id}/accept")
async def accept_decision_record(
    decision_id: int,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.work_product.decision_service import DecisionRecordService
    service = DecisionRecordService(db)
    try:
        dr = await service.accept_decision(decision_id=decision_id, user_id=current_user.id)
        await db.commit()
        return dr
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Phase F: Master Dashboard Summary Endpoint ---

@router.get("/dashboard-summary")
async def get_control_plane_dashboard_summary(
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    from app.workforce.dashboard_service import ControlPlaneDashboardService
    service = ControlPlaneDashboardService(db)
    return await service.get_dashboard_summary(workspace_id=current_user.workspace_id)


# --- Runtime Capabilities & Health Endpoints ---

@router.get("/runtimes")
async def list_runtimes():
    """Liệt kê tất cả các runtime adapters khả dụng trong hệ thống."""
    return [
        {"id": "claude", "name": "Claude Code / Anthropic API", "provider": "anthropic", "profile": "reasoning"},
        {"id": "deepseek", "name": "DeepSeek Reasoner / Chat", "provider": "deepseek", "profile": "deep_reasoning"},
        {"id": "gemini", "name": "Google Gemini 2.0 Flash / ADK", "provider": "google", "profile": "fast"},
        {"id": "http", "name": "Generic HTTP / Ollama / Local", "provider": "local_or_generic", "profile": "local"},
    ]




@router.get("/runtimes/{adapter_key}/capabilities")
async def get_runtime_capabilities(adapter_key: str):
    """Kiểm tra capabilities và liveness của một runtime adapter cụ thể."""
    adapter = RuntimeAdapterFactory.get_adapter(provider=adapter_key)
    capabilities = await adapter.check_capability()
    health = await adapter.health()
    return {
        "adapter_key": adapter_key,
        "capabilities": capabilities,
        "health": health,
    }


# --- Phase 6: Stage-Aware Workforce Roster ---

@router.get("/stage-roster")
async def get_stage_workforce_roster(
    stage: str = Query(..., description="Stage code: S0, S1, S2, S3, S4, S5, S6 hoặc full enum string"),
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lấy Agent Roster được lọc và xếp hạng theo Stage Policy hiện tại.

    Trả về danh sách agent với priority (HIGH/MEDIUM/LOW), fit_score (0–100),
    is_locked, và stage_recommendation cho từng agent.
    Sắp xếp: HIGH priority → MEDIUM → LOW (locked ở cuối).
    """
    from app.workforce.stage_workforce_service import StageAwareWorkforceService
    from app.workforce.registry.agent_registry import AgentRegistryService

    service = StageAwareWorkforceService(db)

    # Seed agents nếu chưa có
    registry = AgentRegistryService(db)
    agents = await registry.list_agents(workspace_id=current_user.workspace_id)
    if not agents:
        await registry.seed_factory_defaults(workspace_id=current_user.workspace_id)
        await db.commit()

    roster = await service.get_stage_roster(
        stage_code=stage,
        workspace_id=current_user.workspace_id,
    )

    # Thêm tóm tắt stage policy vào response header
    stage_summary = service.get_stage_summary(stage)

    return {
        "stage": stage_summary,
        "roster": roster,
        "summary": {
            "total": len(roster),
            "high_priority": sum(1 for a in roster if a["priority"] == "HIGH"),
            "medium": sum(1 for a in roster if a["priority"] == "MEDIUM"),
            "locked": sum(1 for a in roster if a["is_locked"]),
        },
    }


@router.get("/agents/{agent_key}/stage-fit")
async def check_agent_stage_fit(
    agent_key: str,
    stage: str = Query(...),
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    """Kiểm tra mức độ phù hợp của một agent cụ thể với stage."""
    from app.workforce.stage_workforce_service import StageAwareWorkforceService
    service = StageAwareWorkforceService(db)
    fit = await service.check_stage_fit(
        agent_key=agent_key,
        stage_code=stage,
        workspace_id=current_user.workspace_id,
    )
    return {"agent_key": agent_key, **fit}


# --- Phase 6: Exception Escalation Engine ---

class EscalationResolveRequest(BaseModel):
    action: str  # 'retry' | 'reassign' | 'force_approve' | 'dismiss' | 'increase_budget' | 'block_permanently'
    comment: Optional[str] = None


class StageMismatchReportRequest(BaseModel):
    agent_key: str
    agent_name: str
    stage_code: str
    deemphasized_domains: Optional[List[str]] = None


@router.get("/exceptions")
async def list_exception_escalations(
    status: Optional[str] = Query("OPEN", description="OPEN | RESOLVED | DISMISSED | None=all"),
    exception_type: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    """
    Danh sách Exception Escalation Records.
    Mặc định chỉ trả về OPEN escalations đang cần xử lý.
    """
    from app.workforce.governance.exception_engine import ExceptionEscalationEngine
    engine = ExceptionEscalationEngine(db)
    records = await engine.list_active_escalations(
        workspace_id=current_user.workspace_id,
        status=status if status else None,
        exception_type=exception_type,
        tier=tier,
        limit=limit,
    )

    # Tóm tắt theo tier
    founder_gate_count = sum(1 for r in records if r.get("tier") == "FOUNDER_GATE")
    lead_notify_count = sum(1 for r in records if r.get("tier") == "LEAD_NOTIFY")

    return {
        "total": len(records),
        "founder_gate_count": founder_gate_count,
        "lead_notify_count": lead_notify_count,
        "has_critical": founder_gate_count > 0,
        "escalations": records,
    }


@router.post("/exceptions/{escalation_id}/resolve")
async def resolve_exception_escalation(
    escalation_id: int,
    req: EscalationResolveRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    """
    Resolve một Exception Escalation với action cụ thể.

    Actions:
    - 'retry': Yêu cầu hệ thống retry agent run
    - 'reassign': Giao lại task cho agent khác
    - 'force_approve': Chấp thuận cho phép tiếp tục (bỏ qua policy)
    - 'dismiss': Bỏ qua, không cần hành động
    - 'increase_budget': Tăng hạn mức ngân sách
    - 'block_permanently': Khóa vĩnh viễn agent này ở stage hiện tại
    """
    from app.workforce.governance.exception_engine import ExceptionEscalationEngine
    engine = ExceptionEscalationEngine(db)
    try:
        record = await engine.resolve_escalation(
            escalation_id=escalation_id,
            action=req.action,
            comment=req.comment,
            resolved_by=str(current_user.id),
            workspace_id=current_user.workspace_id,
        )
        await db.commit()
        return {"status": "resolved", "escalation": record}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/exceptions/stage-mismatch")
async def report_stage_mismatch(
    req: StageMismatchReportRequest,
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    """
    Báo cáo STAGE_MISMATCH khi agent thuộc domain bị deemphasized được kích hoạt.
    Được gọi từ frontend khi Founder kích hoạt agent bị marked as 'locked' trong Stage Roster.
    """
    from app.workforce.governance.exception_engine import ExceptionEscalationEngine
    engine = ExceptionEscalationEngine(db)
    record = await engine.create_stage_mismatch_escalation(
        agent_key=req.agent_key,
        agent_name=req.agent_name,
        stage_code=req.stage_code,
        workspace_id=current_user.workspace_id,
        deemphasized_domains=req.deemphasized_domains,
    )
    if record:
        await db.commit()
    return record or {"status": "duplicate_skipped"}


@router.post("/exceptions/watchdog-scan")
async def run_exception_watchdog(
    stall_timeout_minutes: int = Query(15, ge=5, le=120),
    db: AsyncSession = Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    """
    Chạy manual watchdog scan để phát hiện stall + budget overflow.
    Tương tự background job tự động nhưng trigger theo yêu cầu.
    """
    from app.workforce.governance.exception_engine import ExceptionEscalationEngine
    engine = ExceptionEscalationEngine(db)

    stall_escalations = await engine.detect_and_escalate_stall(
        workspace_id=current_user.workspace_id,
        stall_timeout_minutes=stall_timeout_minutes,
    )
    budget_escalations = await engine.detect_and_escalate_budget_overflow(
        workspace_id=current_user.workspace_id,
    )
    await db.commit()

    return {
        "stall_detected": len(stall_escalations),
        "budget_overflow_detected": len(budget_escalations),
        "new_escalations": stall_escalations + budget_escalations,
    }




