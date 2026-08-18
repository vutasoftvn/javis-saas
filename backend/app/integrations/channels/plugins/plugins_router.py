from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember, Plugin, WorkspacePlugin

router = APIRouter()

def _require_owner(member: WorkspaceMember):
    # §4.2: "owner: ... quản lý secret/plugin" - các role khác (kể cả admin) không
    # được bật/tắt plugin. Trước đó bất kỳ role nào (kể cả viewer) cũng gọi được.
    if member.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only workspace owner can manage plugins")

@router.get("/")
def list_plugins(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    plugins = db.query(Plugin).all()
    return {"plugins": [{"id": str(p.id), "slug": p.slug, "version": p.version} for p in plugins]}

@router.post("/workspace-plugins/{plugin_id}/enable")
def enable_plugin(
    plugin_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    _require_owner(member)
    # Mock enable plugin logic (manifest/permission check thật để phase sau).
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
        
    wp = db.query(WorkspacePlugin).filter(
        WorkspacePlugin.workspace_id == workspace_id,
        WorkspacePlugin.plugin_id == plugin_id
    ).first()
    
    if not wp:
        wp = WorkspacePlugin(workspace_id=workspace_id, plugin_id=plugin_id, enabled=True)
        db.add(wp)
    else:
        wp.enabled = True
        
    db.commit()
    return {"status": "success", "message": f"Plugin {plugin.slug} enabled"}

@router.post("/workspace-plugins/{plugin_id}/disable")
def disable_plugin(
    plugin_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    _require_owner(member)

    wp = db.query(WorkspacePlugin).filter(
        WorkspacePlugin.workspace_id == workspace_id,
        WorkspacePlugin.plugin_id == plugin_id
    ).first()

    if wp:
        wp.enabled = False
        db.commit()
        
    return {"status": "success", "message": "Plugin disabled"}
