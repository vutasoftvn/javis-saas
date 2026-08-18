from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import Brain, WorkspaceMember
from app.db.repositories.vault_repo import check_permission
from app.founder_os.strategy.models import WorkspaceTemplate
from app.founder_os.strategy.template_service import TemplateService

router = APIRouter()


def _service(workspace_id: int, member: WorkspaceMember, db: Session) -> TemplateService:
    brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
    return TemplateService(db, workspace_id, brain.id)


def _serialize_template(service: TemplateService, template: WorkspaceTemplate) -> dict:
    active_version = service.get_active_version(template)
    return {
        "id": str(template.id),
        "name": template.name,
        "source_key": template.source_key,
        "active_version_no": template.active_version_no,
        "capabilities": (active_version.config_jsonb or {}).get("capabilities", []) if active_version else [],
    }


@router.get("/workspace-templates")
def list_workspace_templates(workspace_id: int,
                              member: WorkspaceMember = Depends(get_current_workspace_member),
                              db: Session = Depends(get_db)):
    service = _service(workspace_id, member, db)
    templates = service.list_templates()
    return {"templates": [_serialize_template(service, t) for t in templates]}


@router.post("/workspace-templates:provision")
def provision_workspace_templates(workspace_id: int,
                                   member: WorkspaceMember = Depends(get_current_workspace_member),
                                   db: Session = Depends(get_db)):
    check_permission(member.role, "admin")
    service = _service(workspace_id, member, db)
    created = service.provision_workspace_templates()
    return {"templates": [_serialize_template(service, t) for t in created]}


@router.post("/workspace-templates/{template_id}:reset")
def reset_workspace_template(template_id: int, workspace_id: int,
                              member: WorkspaceMember = Depends(get_current_workspace_member),
                              db: Session = Depends(get_db)):
    check_permission(member.role, "admin")
    service = _service(workspace_id, member, db)
    template = service.reset_template(template_id, member.user_id)
    return _serialize_template(service, template)


@router.put("/workspace-templates/{template_id}")
def update_workspace_template(template_id: int, workspace_id: int,
                              payload: dict,
                              member: WorkspaceMember = Depends(get_current_workspace_member),
                              db: Session = Depends(get_db)):
    check_permission(member.role, "admin")
    service = _service(workspace_id, member, db)
    template = service.update_template(
        template_id=template_id,
        name=payload.get("name"),
        capabilities=payload.get("capabilities"),
    )
    return _serialize_template(service, template)

