from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
from pydantic import BaseModel

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember, MCPConnection
from app.modules.integrations.secrets_service import encrypt_for_workspace

router = APIRouter()

class ConnectorCreate(BaseModel):
    name: str
    config_jsonb: dict

@router.get("/")
def list_connectors(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    connectors = db.query(MCPConnection).filter(MCPConnection.workspace_id == workspace_id).all()
    return {
        "connectors": [
            {
                "id": str(c.id),
                "name": c.name,
                "status": c.status,
                "created_at": c.created_at.isoformat()
            } for c in connectors
        ]
    }

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_connector(
    workspace_id: uuid.UUID,
    data: ConnectorCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    # For MVP, we just encrypt API keys if they exist in config_jsonb
    config = data.config_jsonb.copy()
    if "api_key" in config:
        config["api_key"] = encrypt_for_workspace(workspace_id, config["api_key"])
        
    connector = MCPConnection(
        workspace_id=workspace_id,
        name=data.name,
        config_jsonb=config,
        status="connected" # mock status
    )
    db.add(connector)
    db.commit()
    db.refresh(connector)
    
    return {
        "id": str(connector.id),
        "name": connector.name,
        "status": connector.status,
        "created_at": connector.created_at.isoformat()
    }

@router.delete("/{connector_id}")
def delete_connector(
    connector_id: uuid.UUID,
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    connector = db.query(MCPConnection).filter(
        MCPConnection.id == connector_id,
        MCPConnection.workspace_id == workspace_id
    ).first()
    
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
        
    db.delete(connector)
    db.commit()
    return {"status": "success", "message": "Connector deleted"}
