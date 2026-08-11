from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember, Agent

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
        "created_at": agent.created_at.isoformat(),
        "updated_at": agent.updated_at.isoformat()
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
