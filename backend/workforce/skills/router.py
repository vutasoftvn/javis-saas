"""FastAPI Router for Global Skill Registry & Lifecycle Management (Spec §61, §62, §P5)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.session import get_db
from platform_core.auth.models import User
from core.auth import get_current_user
from workforce.skills.service import SkillLifecycleService
from workforce.skills.models import SkillRegistryItem

router = APIRouter()


# Schemas
class CreateSkillCandidateRequest(BaseModel):
    workspace_id: int
    name: str
    domain: str
    instructions: str
    description: str = ""
    scope: List[str] = Field(default_factory=list)
    tool_permissions: List[str] = Field(default_factory=list)
    required_context: List[str] = Field(default_factory=list)
    created_by_agent: Optional[str] = None


class TrajectoryCandidateRequest(BaseModel):
    workspace_id: int
    domain: str
    proposed_name: str
    extracted_sop: str
    mission_id: Optional[str] = None
    run_id: Optional[int] = None
    tools_used: List[str] = Field(default_factory=list)


class EvaluateSkillRequest(BaseModel):
    eval_score: float = Field(ge=0.0, le=1.0)
    eval_details: Optional[Dict[str, Any]] = None


class DeprecateSkillRequest(BaseModel):
    reason: Optional[str] = None


class ArchiveSkillRequest(BaseModel):
    reason: Optional[str] = None


class BlockSkillRequest(BaseModel):
    reason: str


class PromoteSkillRequest(BaseModel):
    target_status: str = Field(default="active", pattern="^(active|experimental)$")


class SkillFeedbackRequest(BaseModel):
    success: bool
    rating: Optional[int] = Field(default=None, ge=1, le=5)


class UpdateSkillRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    tool_permissions: Optional[List[str]] = None
    domain: Optional[str] = None
    version: Optional[str] = None


class UploadSkillMarkdownRequest(BaseModel):
    markdown_content: str
    domain: Optional[str] = None
    name: Optional[str] = None
    auto_promote: bool = True



class SkillItemResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    domain: str
    version: str
    status: str
    is_system: bool
    description: str
    instructions: str
    scope: List[str]
    tool_permissions: List[str]
    required_context: List[str]
    success_rate: float
    usage_count: int
    positive_feedback: int
    negative_feedback: int
    created_by_agent: Optional[str]
    approved_by_user_id: Optional[str]
    approved_at: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_orm_model(cls, item: SkillRegistryItem) -> "SkillItemResponse":
        return cls(
            id=str(item.id),
            workspace_id=str(item.workspace_id),
            name=item.name,
            domain=item.domain,
            version=item.version,
            status=item.status,
            is_system=bool(item.is_system),
            description=item.description or "",
            instructions=item.instructions or "",
            scope=item.scope or [],
            tool_permissions=item.tool_permissions or [],
            required_context=item.required_context or [],
            success_rate=item.success_rate,
            usage_count=item.usage_count,
            positive_feedback=item.positive_feedback,
            negative_feedback=item.negative_feedback,
            created_by_agent=item.created_by_agent,
            approved_by_user_id=str(item.approved_by_user_id) if item.approved_by_user_id else None,
            approved_at=item.approved_at.isoformat() if item.approved_at else None,
            created_at=item.created_at.isoformat(),
            updated_at=item.updated_at.isoformat(),
        )


@router.get("", response_model=List[SkillItemResponse])
def list_skills(
    workspace_id: int = Query(...),
    domain: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List skills for workspace with optional domain and status filters. Auto-seeds built-in skills if empty."""
    total_existing = db.query(SkillRegistryItem).filter(SkillRegistryItem.workspace_id == workspace_id).count()
    if total_existing == 0:
        try:
            from pathlib import Path
            from workforce.skills.skill_loader import DynamicSkillLoader

            loader = DynamicSkillLoader(None, str(Path(__file__).parent))
            docs = loader.scan_physical_skills()
            for doc in docs:
                # G3 Phase 1C: platform-shipped content, not a human clicking approve -
                # seed_platform_skill() records that honestly (is_system=True, no
                # approved_by_user_id) instead of attributing approval to whichever
                # user happened to be first to GET this list.
                SkillLifecycleService.seed_platform_skill(
                    db=db,
                    workspace_id=workspace_id,
                    name=doc.name,
                    domain=doc.department.lower(),
                    instructions=doc.content_markdown,
                    description=doc.description,
                    scope=[],
                    tool_permissions=doc.required_tools,
                    required_context=[],
                )
        except Exception:
            db.rollback()

    items = SkillLifecycleService.list_skills(db, workspace_id, domain, status)
    return [SkillItemResponse.from_orm_model(item) for item in items]


@router.post("/sync-built-in", response_model=List[SkillItemResponse])
def sync_built_in_skills(
    workspace_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Đồng bộ toàn bộ bộ Kỹ năng tích hợp sẵn (Built-in SKILL.md) vào database của Workspace."""
    from workforce.skills.skill_loader import DynamicSkillLoader

    ws_id = int(workspace_id) if (workspace_id and workspace_id.isdigit()) else (current_user.workspace_id or 1)
    loader = DynamicSkillLoader(None)
    docs = loader.scan_physical_skills()
    synced_items = []

    for doc in docs:
        try:
            existing = (
                db.query(SkillRegistryItem)
                .filter(
                    SkillRegistryItem.workspace_id == ws_id,
                    SkillRegistryItem.name == doc.name,
                )
                .first()
            )
            if not existing:
                item = SkillLifecycleService.seed_platform_skill(
                    db=db,
                    workspace_id=ws_id,
                    name=doc.name,
                    domain=doc.department.lower(),
                    instructions=doc.content_markdown,
                    description=doc.description or f"Quy trình kỹ năng chuẩn {doc.name}",
                    scope=[],
                    tool_permissions=doc.required_tools,
                    required_context=[],
                )
                synced_items.append(item)
            else:
                synced_items.append(existing)
        except Exception:
            db.rollback()

    return [SkillItemResponse.from_orm_model(item) for item in synced_items]



@router.get("/{skill_id}", response_model=SkillItemResponse)
def get_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single skill by ID."""
    item = db.query(SkillRegistryItem).filter(SkillRegistryItem.id == skill_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Skill not found")
    return SkillItemResponse.from_orm_model(item)


@router.put("/{skill_id}", response_model=SkillItemResponse)
def update_skill(
    skill_id: int,
    req: UpdateSkillRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cập nhật thông tin kỹ năng: Name, Description, SOP Instructions, Tool Permissions."""
    try:
        item = SkillLifecycleService.update_skill(
            db=db,
            skill_id=skill_id,
            name=req.name,
            description=req.description,
            instructions=req.instructions,
            tool_permissions=req.tool_permissions,
            domain=req.domain,
            version=req.version,
        )
        return SkillItemResponse.from_orm_model(item)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))



@router.post("/candidates", response_model=SkillItemResponse, status_code=status.HTTP_201_CREATED)
def create_skill_candidate(
    req: CreateSkillCandidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new skill candidate."""
    try:
        item = SkillLifecycleService.register_skill_candidate(
            db=db,
            workspace_id=req.workspace_id,
            name=req.name,
            domain=req.domain,
            instructions=req.instructions,
            description=req.description,
            scope=req.scope,
            tool_permissions=req.tool_permissions,
            required_context=req.required_context,
            created_by_agent=req.created_by_agent,
        )
        return SkillItemResponse.from_orm_model(item)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/trajectory-candidate")
def create_from_trajectory(
    req: TrajectoryCandidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract and scan learning candidate from completed mission trajectory."""
    cand = SkillLifecycleService.create_candidate_from_trajectory(
        db=db,
        workspace_id=req.workspace_id,
        domain=req.domain,
        proposed_name=req.proposed_name,
        extracted_sop=req.extracted_sop,
        mission_id=req.mission_id,
        run_id=req.run_id,
        tools_used=req.tools_used,
    )
    return {
        "id": str(cand.id),
        "domain": cand.domain,
        "proposed_name": cand.proposed_name,
        "pii_scan_passed": cand.pii_scan_passed,
        "secret_scan_passed": cand.secret_scan_passed,
        "safety_notes": cand.safety_notes,
        "status": cand.status,
    }


@router.post("/{skill_id}/evaluate", response_model=SkillItemResponse)
def evaluate_skill(
    skill_id: int,
    req: EvaluateSkillRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record evaluation score for a skill candidate."""
    try:
        item = SkillLifecycleService.evaluate_skill(db, skill_id, req.eval_score, req.eval_details)
        return SkillItemResponse.from_orm_model(item)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{skill_id}/promote", response_model=SkillItemResponse)
def promote_skill(
    skill_id: int,
    req: Optional[PromoteSkillRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Promote an evaluated skill to active (or experimental) production status.

    INVARIANT ENFORCEMENT:
    NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS.
    Only authenticated human users can promote.
    """
    try:
        item = SkillLifecycleService.promote_skill(
            db=db,
            skill_id=skill_id,
            approved_by_user_id=current_user.id,
            target_status=(req.target_status if req else "active"),
        )
        return SkillItemResponse.from_orm_model(item)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{skill_id}/deprecate", response_model=SkillItemResponse)
def deprecate_skill(
    skill_id: int,
    req: DeprecateSkillRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deprecate a skill (soft retirement - discouraged, may still run)."""
    try:
        item = SkillLifecycleService.deprecate_skill(db, skill_id, current_user.id, req.reason)
        return SkillItemResponse.from_orm_model(item)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{skill_id}/archive", response_model=SkillItemResponse)
def archive_skill(
    skill_id: int,
    req: ArchiveSkillRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archive a skill - terminal retirement, excluded from normal listing/use."""
    try:
        item = SkillLifecycleService.archive_skill(db, skill_id, current_user.id, req.reason)
        return SkillItemResponse.from_orm_model(item)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{skill_id}/block", response_model=SkillItemResponse)
def block_skill(
    skill_id: int,
    req: BlockSkillRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Emergency kill-switch: forcibly disable a skill regardless of its current status."""
    try:
        item = SkillLifecycleService.block_skill(db, skill_id, current_user.id, req.reason)
        return SkillItemResponse.from_orm_model(item)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{skill_id}/feedback", response_model=SkillItemResponse)
def record_skill_feedback(
    skill_id: int,
    req: SkillFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record runtime feedback/rating for a skill run."""
    try:
        item = SkillLifecycleService.record_usage(db, skill_id, req.success, req.rating)
        return SkillItemResponse.from_orm_model(item)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/upload-markdown", response_model=SkillItemResponse)
def upload_skill_markdown(

    req: UploadSkillMarkdownRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Nạp file hoặc nội dung SKILL.md (YAML Frontmatter + Markdown SOP) trực tiếp cho Workspace."""
    import yaml
    raw = req.markdown_content
    frontmatter = {}
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()
            except Exception:
                pass

    name = req.name or frontmatter.get("name") or "Custom Skill SOP"
    domain = req.domain or frontmatter.get("department") or frontmatter.get("domain") or "General"
    description = frontmatter.get("description", "")
    tools = frontmatter.get("required_tools", [])

    item = SkillLifecycleService.register_skill_candidate(
        db=db,
        workspace_id=current_user.workspace_id,
        name=name,
        domain=domain,
        instructions=body,
        description=description,
        tool_permissions=tools if isinstance(tools, list) else [],
    )

    if req.auto_promote:
        item = SkillLifecycleService.promote_skill(
            db=db,
            skill_id=item.id,
            approved_by_user_id=current_user.id,
        )

    return SkillItemResponse.from_orm_model(item)
