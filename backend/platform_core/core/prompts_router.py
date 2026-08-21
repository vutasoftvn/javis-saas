from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from workforce.ai.prompt_registry import PromptRegistry
from core.auth import get_current_workspace_member
from core.authz import authorize
from core.protected_resources import service as protected_resource_service
from core.protected_resources.models import ProtectedResource
from db.models import WorkspaceMember
from db.session import get_db

router = APIRouter()

# Domain prompts actively wired to runtime call sites
WIRED_PROMPTS = {
    ("cosa", "chat_language"),
    ("cosa", "chat_conversation"),
    ("cosa", "chat_structured_oneshot"),
    ("cosa", "chief_of_staff_synthesis"),
    ("cosa", "grounding"),
    ("cosa", "no_tools"),
    ("cosa", "ungrounded_action"),
    ("sales", "outreach"),
}


class DomainPromptUpdate(BaseModel):
    content: str


def _resource_key(domain: str, name: str) -> str:
    return f"{domain}/{name}"


def _require_known_prompt(domain: str, name: str):
    template = PromptRegistry.get_instance().get(domain, name)
    if not template:
        raise HTTPException(status_code=404, detail=f"Unknown prompt '{domain}/{name}'")
    return template


@router.get("/")
def list_domain_prompts(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    authorize(member, "prompt.read")
    registry = PromptRegistry.get_instance()
    result = []
    for meta in sorted(registry.list_templates().values(), key=lambda t: (t["domain"], t["name"])):
        domain, name = meta["domain"], meta["name"]
        resource = (
            db.query(ProtectedResource)
            .filter(
                ProtectedResource.workspace_id == workspace_id,
                ProtectedResource.resource_type == "domain_prompt",
                ProtectedResource.resource_key == _resource_key(domain, name),
            )
            .first()
        )
        result.append({
            "domain": domain,
            "name": name,
            "is_overridden": bool(resource and resource.active_revision_no != 0),
            "is_wired": (domain, name) in WIRED_PROMPTS,
            "updated_at": resource.updated_at.isoformat() if resource else None,
        })
    return {"prompts": result}


@router.get("/{domain}/{name}")
def get_domain_prompt(
    workspace_id: int,
    domain: str,
    name: str,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    authorize(member, "prompt.read")
    template = _require_known_prompt(domain, name)

    effective = protected_resource_service.get_effective(
        db=db, workspace_id=workspace_id, resource_type="domain_prompt",
        resource_key=_resource_key(domain, name),
        default_content={"content": template.content},
    )
    revisions = protected_resource_service.list_revisions(
        db=db, workspace_id=workspace_id, resource_type="domain_prompt",
        resource_key=_resource_key(domain, name),
    )
    return {
        "domain": domain,
        "name": name,
        "content": effective.get("content", template.content),
        "default_content": template.content,
        "is_wired": (domain, name) in WIRED_PROMPTS,
        "revisions": [
            {
                "id": str(r.id),
                "revision_no": r.revision_no,
                "content": r.content_jsonb.get("content"),
                "is_default": r.is_default,
                "status": r.status,
                "created_by": str(r.created_by) if r.created_by else None,
                "checksum": r.checksum,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in revisions
        ],
    }


@router.patch("/{domain}/{name}")
def update_domain_prompt(
    workspace_id: int,
    domain: str,
    name: str,
    payload: DomainPromptUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    authorize(member, "prompt.update")
    template = _require_known_prompt(domain, name)

    protected_resource_service.create_revision(
        db=db, workspace_id=workspace_id, resource_type="domain_prompt",
        resource_key=_resource_key(domain, name),
        content={"content": payload.content},
        actor_id=member.user_id,
        default_content={"content": template.content},
    )
    return {"domain": domain, "name": name, "content": payload.content}


@router.post("/{domain}/{name}:reset")
def reset_domain_prompt(
    workspace_id: int,
    domain: str,
    name: str,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    authorize(member, "prompt.reset")
    template = _require_known_prompt(domain, name)

    protected_resource_service.reset_to_default(
        db=db, workspace_id=workspace_id, resource_type="domain_prompt",
        resource_key=_resource_key(domain, name), actor_id=member.user_id,
    )
    return {"status": "reset", "domain": domain, "name": name, "content": template.content}
