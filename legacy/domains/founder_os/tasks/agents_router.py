"""Legacy CRUD router for standalone Agent models and protected prompt revisions.

WARNING / LƯU Ý KIẾN TRÚC:
- Route này (`/api/v1/agents`) thao tác trực tiếp trên bảng legacy `agents` (model `Agent`),
  chủ yếu phục vụ prompt revisions (`protected_resource_service`) và client cũ.
- Để tuyển dụng/tạo AI Employee chuẩn mực trong hệ thống hybrid workforce (bao gồm
  `AgentDefinition` + `WorkforceMember` + `WorkforceRelation`), sử dụng:
  `app.platform.organization.service::hire_ai_employee()` hoặc API `/api/v1/organization/ai-employees`.
- KHÔNG sử dụng router này để khởi tạo nhân sự AI mới trong pipeline delegation/orchestration.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from db.session import get_db
from core.auth import get_current_workspace_member
from core.authz import authorize
from core.protected_resources import service as protected_resource_service
from db.models import WorkspaceMember, Agent

router = APIRouter()

class AgentCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None

@router.get("/")
def list_agents(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    agents = db.query(Agent).filter(Agent.workspace_id == workspace_id).order_by(Agent.created_at.desc()).all()
    return {
        "agents": [
            {
                "id": str(a.id),
                "name": a.name,
                "slug": a.slug,
                "description": a.description,
                "system_prompt": a.system_prompt,
                "provider": a.provider,
                "model": a.model,
                "created_at": a.created_at.isoformat(),
                "updated_at": a.updated_at.isoformat()
            } for a in agents
        ]
    }

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_agent(
    workspace_id: int,
    agent_in: AgentCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    existing = db.query(Agent).filter(
        Agent.workspace_id == workspace_id,
        Agent.slug == agent_in.slug
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Agent with this slug already exists")

    agent = Agent(
        workspace_id=workspace_id,
        name=agent_in.name,
        slug=agent_in.slug,
        description=agent_in.description,
        system_prompt=agent_in.system_prompt,
        provider=agent_in.provider,
        model=agent_in.model
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    return {
        "id": str(agent.id),
        "name": agent.name,
        "slug": agent.slug,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "provider": agent.provider,
        "model": agent.model,
        "created_at": agent.created_at.isoformat(),
        "updated_at": agent.updated_at.isoformat()
    }

@router.patch("/{agent_id}")
def update_agent(
    workspace_id: int,
    agent_id: int,
    agent_in: AgentUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(
        Agent.workspace_id == workspace_id,
        Agent.id == agent_id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent_in.name is not None:
        agent.name = agent_in.name
    if agent_in.slug is not None:
        agent.slug = agent_in.slug
    if agent_in.description is not None:
        agent.description = agent_in.description
    if agent_in.system_prompt is not None:
        authorize(member, "prompt.update")
        protected_resource_service.create_revision(
            db=db,
            workspace_id=workspace_id,
            resource_type="agent_prompt",
            resource_key=f"agent:{agent_id}:system_prompt",
            content={"system_prompt": agent_in.system_prompt},
            actor_id=member.user_id,
            default_content={"system_prompt": agent.system_prompt or ""},
        )
        agent.system_prompt = agent_in.system_prompt
    if agent_in.provider is not None:
        agent.provider = agent_in.provider
    if agent_in.model is not None:
        agent.model = agent_in.model
        
    db.commit()
    db.refresh(agent)
    
    return {
        "id": str(agent.id),
        "name": agent.name,
        "slug": agent.slug,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "provider": agent.provider,
        "model": agent.model,
        "created_at": agent.created_at.isoformat() if agent.created_at else datetime.utcnow().isoformat(),
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else datetime.utcnow().isoformat()
    }

@router.post("/{agent_id}/system_prompt:reset")
def reset_agent_system_prompt(
    workspace_id: int,
    agent_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    authorize(member, "prompt.reset")
    agent = db.query(Agent).filter(
        Agent.workspace_id == workspace_id,
        Agent.id == agent_id,
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    protected_resource_service.reset_to_default(
        db=db,
        workspace_id=workspace_id,
        resource_type="agent_prompt",
        resource_key=f"agent:{agent_id}:system_prompt",
        actor_id=member.user_id,
    )
    effective = protected_resource_service.get_effective(
        db=db,
        workspace_id=workspace_id,
        resource_type="agent_prompt",
        resource_key=f"agent:{agent_id}:system_prompt",
    )
    agent.system_prompt = effective.get("system_prompt", "")
    db.commit()
    db.refresh(agent)

    return {
        "status": "reset",
        "agent_id": str(agent.id),
        "system_prompt": agent.system_prompt,
    }

@router.get("/{agent_id}/system_prompt/revisions")
def list_agent_prompt_revisions(
    workspace_id: int,
    agent_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    authorize(member, "prompt.read")
    agent = db.query(Agent).filter(
        Agent.workspace_id == workspace_id,
        Agent.id == agent_id,
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    revisions = protected_resource_service.list_revisions(
        db=db,
        workspace_id=workspace_id,
        resource_type="agent_prompt",
        resource_key=f"agent:{agent_id}:system_prompt",
    )
    return {
        "revisions": [
            {
                "id": str(r.id),
                "revision_no": r.revision_no,
                "content": r.content_jsonb,
                "is_default": r.is_default,
                "status": r.status,
                "created_by": str(r.created_by) if r.created_by else None,
                "checksum": r.checksum,
                "created_at": r.created_at.isoformat() if r.created_at else datetime.utcnow().isoformat(),
            }
            for r in revisions
        ]
    }

@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    workspace_id: int,
    agent_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(
        Agent.workspace_id == workspace_id,
        Agent.id == agent_id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    db.delete(agent)
    db.commit()
    return None
