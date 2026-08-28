from __future__ import annotations

import logging
from pathlib import Path
import re
from typing import Any, Optional
import uuid
import yaml

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from agent_core.contracts.identity import PinnedSkillRef
from agent_core.registry.publisher import publish_skill_spec
from agent_core.registry.repository import SpecVersionHashConflictError
from agent_core.skills.candidate_store import (
    InMemorySkillCandidateStore,
    SkillCandidateStore,
    SkillFeedbackRecord,
)
from agent_core.skills.contracts import (
    SkillCandidate,
    SkillSpec,
    SkillStatus,
)
from agent_core.skills.skillpack_contract import (
    _extract_source_attribution_record,
    _parse_skillmd_frontmatter,
    get_registered_capability_ids,
    validate_skillpack_tree,
)
from apps.cosa.api.routes import get_cosa_plane
from apps.cosa.api.skill_schemas import (
    CreateCandidateRequest,
    DeprecateSkillRequest,
    EvaluateSkillRequest,
    EvaluateSkillResponse,
    PromoteSkillRequest,
    SkillFeedbackRequest,
    SkillListItem,
    SyncBuiltInResponse,
    SyncSkillItem,
)
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.composition.agent_plane import CosaAgentPlane

logger = logging.getLogger("cosa.api.skill_registry")

__all__ = ["create_skill_registry_router", "router"]

router = APIRouter(prefix="/agent/skills", tags=["skill-registry"])


def get_skill_candidate_store(request: Request) -> SkillCandidateStore:
    """Dependency injection helper cho SkillCandidateStore."""
    store = getattr(request.app.state, "skill_candidate_store", None)
    if store is None:
        store = InMemorySkillCandidateStore()
        request.app.state.skill_candidate_store = store
    return store


def _find_repo_root() -> Path:
    """Tìm thư mục gốc của repository."""
    # File nằm tại /Volumes/SSD/javis-saas/apps/cosa/api/skill_registry_routes.py
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "skillpacks").is_dir() and (parent / "packages").is_dir():
            return parent
    return current.parents[3]


def _extract_instructions_body(skillmd_text: str) -> str:
    """Tách phần thân markdown sau YAML frontmatter."""
    if not skillmd_text.startswith("---"):
        return skillmd_text.strip()
    parts = skillmd_text.split("---", 2)
    if len(parts) >= 3:
        return parts[2].strip()
    return skillmd_text.strip()


@router.get("", response_model=list[SkillListItem])
async def list_skills(
    request: Request,
    domain: Optional[str] = Query(None, description="Lọc theo domain/category"),
    status: Optional[str] = Query(None, description="Lọc theo status (published, candidate, retired, etc.)"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID"),
    identity: Optional[AuthenticatedIdentity] = Depends(get_authenticated_identity),
    plane: CosaAgentPlane = Depends(get_cosa_plane),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> list[SkillListItem]:
    """Danh sách kỹ năng trong hệ thống (từ published specs và candidates)."""
    ws_id = (
        workspace_id
        or (identity.workspace_id if identity else None)
        or "default_workspace"
    )

    items: list[SkillListItem] = []
    seen_ids: set[str] = set()

    # 1. Published / Retired specs từ SpecRegistryRepository
    records = await plane.spec_registry.list_all(spec_kind="skill")
    for r in records:
        content = r.content or {}
        spec_status = r.status.upper() if r.status else "PUBLISHED"
        spec_domain = content.get("applicability", {}).get("domain") or content.get("domain") or "general"

        if domain and spec_domain.lower() != domain.lower():
            continue
        if status and spec_status.lower() != status.lower():
            continue

        refs = content.get("references") or {}
        raw_origin = refs.get("origin")
        if isinstance(raw_origin, dict):
            origin = raw_origin.get("repository") or raw_origin.get("upstream") or str(raw_origin)
        elif raw_origin is not None:
            origin = str(raw_origin)
        else:
            origin = "built-in"

        raw_sha = refs.get("upstream_commit") or refs.get("commit")
        adapted_sha = str(raw_sha) if raw_sha is not None else None

        item = SkillListItem(
            id=r.spec_id,
            version=r.version,
            name=content.get("name") or r.spec_id,
            description=content.get("description") or "",
            domain=spec_domain,
            status=spec_status,
            definition_hash=r.definition_hash,
            required_capabilities=content.get("required_capabilities") or [],
            origin=origin,
            adapted_from_sha=adapted_sha,
            eval_score=content.get("eval_score"),
            runtime_state="unpinned",
            instructions=content.get("instructions"),
            references=refs,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        items.append(item)
        seen_ids.add(r.spec_id)

    # 2. Candidates từ CandidateStore (workspace-scoped)
    candidates = await candidate_store.list_candidates(ws_id, status=status)
    for c in candidates:
        cand_skill = c.proposed_skill
        cand_domain = cand_skill.applicability.get("domain") if cand_skill.applicability else "general"

        if domain and cand_domain.lower() != domain.lower():
            continue

        raw_cand_origin = cand_skill.references.get("origin", "candidate")
        cand_origin = (
            raw_cand_origin.get("repository") or raw_cand_origin.get("upstream") or str(raw_cand_origin)
            if isinstance(raw_cand_origin, dict)
            else str(raw_cand_origin)
        )

        item = SkillListItem(
            id=cand_skill.id,
            version=cand_skill.version,
            name=cand_skill.name or cand_skill.id,
            description=cand_skill.description,
            domain=cand_domain,
            status=c.status.value,
            definition_hash=cand_skill.definition_hash or cand_skill.compute_hash(),
            required_capabilities=cand_skill.required_capabilities,
            origin=cand_origin,
            adapted_from_sha=cand_skill.references.get("upstream_commit"),
            eval_score=c.eval_score,
            runtime_state="unpinned",
            instructions=cand_skill.instructions,
            references=cand_skill.references,
            candidate_id=c.candidate_id,
            created_at=cand_skill.created_at.isoformat() if cand_skill.created_at else None,
        )
        items.append(item)

    return items


@router.post("/sync-built-in", response_model=SyncBuiltInResponse)
async def sync_built_in_skills(
    request: Request,
    workspace_id: Optional[str] = Query(None),
    identity: Optional[AuthenticatedIdentity] = Depends(get_authenticated_identity),
    plane: CosaAgentPlane = Depends(get_cosa_plane),
) -> SyncBuiltInResponse:
    """Đồng bộ và publish có kiểm tra tất cả built-in skillpacks vào SpecRegistry.

    Chạy validate_skillpack_tree trước; nếu 0 violation, publish từng skillpack
    vào SpecRegistryRepository (idempotent theo hash). KHÔNG đụng cap_registry.
    """
    repo_root = _find_repo_root()
    skillpacks_root = repo_root / "skillpacks"

    if not skillpacks_root.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thư mục skillpacks không tồn tại tại {skillpacks_root}",
        )

    # 1. Chạy validation contract
    violations = validate_skillpack_tree(skillpacks_root)
    if violations:
        violation_details = [
            {"path": str(v.path), "rule": v.rule, "message": v.message}
            for v in violations
        ]
        logger.error("Skillpack validation failed during sync-built-in: %s", violation_details)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"Phát hiện {len(violations)} vi phạm skillpack contract",
                "violations": violation_details,
            },
        )

    # 2. Quét và publish từng skillpack
    registered_caps = get_registered_capability_ids()
    synced_items: list[SyncSkillItem] = []

    for manifest_path in sorted(skillpacks_root.rglob("manifest.yaml")):
        pack_dir = manifest_path.parent
        skillmd_path = pack_dir / "SKILL.md"
        if not skillmd_path.is_file():
            continue

        try:
            manifest_text = manifest_path.read_text(encoding="utf-8")
            manifest_data = yaml.safe_load(manifest_text) or {}
            skillmd_text = skillmd_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("Không thể đọc skillpack tại %s: %s", pack_dir, e)
            continue

        metadata = manifest_data.get("metadata", {})
        skill_id = metadata.get("id") or pack_dir.name
        version = metadata.get("version", "1.0.0")
        name = metadata.get("name", skill_id)
        description = metadata.get("description", "")
        category = metadata.get("category") or pack_dir.parent.name or "general"

        # Capabilities từ manifest.runtime.tools đã lọc
        runtime_config = manifest_data.get("runtime", {})
        raw_tools = runtime_config.get("tools") or manifest_data.get("tools") or []
        required_capabilities = [
            tool for tool in raw_tools
            if isinstance(tool, str)
        ]

        # References / Attribution
        source_config = manifest_data.get("source", {})
        upstream_record = _extract_source_attribution_record(skillmd_text) or {}

        rel_source_path = f"skillpacks/{pack_dir.relative_to(skillpacks_root)}"
        references = {
            "source_path": source_config.get("path") or rel_source_path,
            "origin": upstream_record.get("upstream") or source_config.get("origin") or "built-in",
            "upstream_commit": upstream_record.get("commit") or source_config.get("commit") or "adapted",
        }

        instructions = _extract_instructions_body(skillmd_text)

        spec = SkillSpec(
            id=skill_id,
            version=version,
            name=name,
            description=description,
            instructions=instructions,
            applicability={"domain": category},
            required_capabilities=required_capabilities,
            references=references,
            status=SkillStatus.PUBLISHED,
            publisher="cosa_built_in",
        )

        try:
            record = await publish_skill_spec(
                spec,
                repository=plane.spec_registry,
                publisher="cosa_built_in",
            )
            synced_items.append(
                SyncSkillItem(
                    skill_id=spec.id,
                    version=spec.version,
                    definition_hash=record.definition_hash,
                    published=True,
                    domain=category,
                )
            )
        except SpecVersionHashConflictError as exc:
            logger.error("SpecVersionHashConflictError when syncing skill %s: %s", spec.id, exc)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            )

    logger.info("Đã đồng bộ thành công %d built-in skills", len(synced_items))
    return SyncBuiltInResponse(
        synced_count=len(synced_items),
        skills=synced_items,
    )


@router.post("/candidates", status_code=status.HTTP_201_CREATED)
async def create_candidate(
    req: CreateCandidateRequest,
    request: Request,
    identity: Optional[AuthenticatedIdentity] = Depends(get_authenticated_identity),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> dict[str, Any]:
    """Tạo mới một SkillCandidate trong workspace."""
    ws_id = (
        req.workspace_id
        or (identity.workspace_id if identity else None)
        or "default_workspace"
    )

    skill_id = re.sub(r"[^a-z0-9_-]", "-", req.name.lower()).strip("-")
    if not skill_id:
        skill_id = f"custom-skill-{uuid.uuid4().hex[:6]}"

    spec = SkillSpec(
        id=skill_id,
        version="0.1.0",
        name=req.name,
        description=req.description,
        instructions=req.instructions,
        applicability={"domain": req.domain, "scope": req.scope},
        required_capabilities=req.required_capabilities or req.tool_permissions,
        references={"created_by_agent": req.created_by_agent},
        status=SkillStatus.CANDIDATE,
        publisher=req.created_by_agent or (identity.platform_user_id if identity else "user"),
    )

    candidate = SkillCandidate(
        candidate_id=f"cand_{uuid.uuid4().hex[:12]}",
        parent_run_id=req.created_by_agent or "manual",
        proposed_skill=spec,
        evidence_refs=[],
        eval_score=0.0,
        status=SkillStatus.CANDIDATE,
    )

    saved = await candidate_store.save_candidate(ws_id, candidate)
    return {
        "candidate_id": saved.candidate_id,
        "skill_id": saved.proposed_skill.id,
        "status": saved.status.value,
        "proposed_skill": saved.proposed_skill.model_dump(mode="json"),
    }


@router.post("/{skill_id}/evaluate", response_model=EvaluateSkillResponse)
async def evaluate_skill(
    skill_id: str,
    req: EvaluateSkillRequest,
    request: Request,
    identity: Optional[AuthenticatedIdentity] = Depends(get_authenticated_identity),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> EvaluateSkillResponse:
    """Chạy đánh giá hoặc ghi nhận eval_score cho candidate skill."""
    ws_id = (identity.workspace_id if identity else None) or "default_workspace"
    cand = await candidate_store.get_candidate(ws_id, skill_id)

    if cand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate skill '{skill_id}' không tồn tại trong workspace",
        )

    updated = await candidate_store.update_candidate_status(
        ws_id,
        cand.candidate_id,
        status=SkillStatus.EVALUATED,
        eval_score=req.eval_score,
    )

    return EvaluateSkillResponse(
        skill_id=skill_id,
        eval_score=req.eval_score,
        status=SkillStatus.EVALUATED.value,
        details=req.eval_details,
    )


@router.post("/{skill_id}/promote")
async def promote_skill(
    skill_id: str,
    req: PromoteSkillRequest,
    request: Request,
    identity: Optional[AuthenticatedIdentity] = Depends(get_authenticated_identity),
    plane: CosaAgentPlane = Depends(get_cosa_plane),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> dict[str, Any]:
    """Phê duyệt và đưa Candidate skill vào sản xuất (Published).

    BẮT BUỘC có approved_by và approval_reason (human approval gate).
    """
    if not req.approved_by or not req.approval_reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="approved_by và approval_reason là bắt buộc để promote skill lên sản xuất",
        )

    ws_id = (identity.workspace_id if identity else None) or "default_workspace"
    cand = await candidate_store.get_candidate(ws_id, skill_id)

    if cand is not None:
        spec = cand.proposed_skill.model_copy(deep=True)
        spec.status = SkillStatus.PUBLISHED
        spec.publisher = req.approved_by
        if req.version:
            spec.version = req.version

        try:
            record = await publish_skill_spec(
                spec,
                repository=plane.spec_registry,
                publisher=req.approved_by,
            )
            await candidate_store.update_candidate_status(
                ws_id,
                cand.candidate_id,
                status=SkillStatus.PUBLISHED,
            )
            return {
                "skill_id": spec.id,
                "version": spec.version,
                "status": "PUBLISHED",
                "definition_hash": record.definition_hash,
                "approved_by": req.approved_by,
                "approval_reason": req.approval_reason,
            }
        except SpecVersionHashConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            )

    # Check if existing spec in spec_registry needs reactivation
    existing = await plane.spec_registry.get("skill", skill_id, req.version or "1.0.0")
    if existing is not None:
        updated_rec = await plane.spec_registry.update_status("skill", skill_id, existing.version, "published")
        return {
            "skill_id": skill_id,
            "version": existing.version,
            "status": "PUBLISHED",
            "approved_by": req.approved_by,
            "approval_reason": req.approval_reason,
        }

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Không tìm thấy skill hoặc candidate '{skill_id}' để promote",
    )


@router.post("/{skill_id}/deprecate")
async def deprecate_skill(
    skill_id: str,
    req: DeprecateSkillRequest,
    request: Request,
    identity: Optional[AuthenticatedIdentity] = Depends(get_authenticated_identity),
    plane: CosaAgentPlane = Depends(get_cosa_plane),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> dict[str, Any]:
    """Chuyển trạng thái Skill sang RETIRED (không xoá bản ghi)."""
    ws_id = (identity.workspace_id if identity else None) or "default_workspace"

    # 1. Update in spec_registry if published
    versions = await plane.spec_registry.list_versions("skill", skill_id)
    deprecated = False
    for v in versions:
        await plane.spec_registry.update_status("skill", skill_id, v.version, "retired")
        deprecated = True

    # 2. Update in candidate_store if candidate
    cand = await candidate_store.get_candidate(ws_id, skill_id)
    if cand is not None:
        await candidate_store.update_candidate_status(ws_id, cand.candidate_id, status=SkillStatus.RETIRED)
        deprecated = True

    if not deprecated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_id}' không tồn tại",
        )

    return {
        "skill_id": skill_id,
        "status": "RETIRED",
        "reason": req.reason,
    }


@router.post("/{skill_id}/feedback")
async def record_skill_feedback(
    skill_id: str,
    req: SkillFeedbackRequest,
    request: Request,
    identity: Optional[AuthenticatedIdentity] = Depends(get_authenticated_identity),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> dict[str, Any]:
    """Ghi nhận phản hồi kết quả thực thi kỹ năng."""
    ws_id = (identity.workspace_id if identity else None) or "default_workspace"

    fb = SkillFeedbackRecord(
        workspace_id=ws_id,
        skill_id=skill_id,
        success=req.success,
        rating=req.rating,
        notes=req.notes,
    )
    saved = await candidate_store.save_feedback(fb)
    return {
        "status": "ok",
        "feedback_id": saved.feedback_id,
        "skill_id": skill_id,
        "recorded": True,
    }


@router.get("/{skill_id}")
async def get_skill(
    skill_id: str,
    version: Optional[str] = Query(None),
    workspace_id: Optional[str] = Query(None),
    identity: Optional[AuthenticatedIdentity] = Depends(get_authenticated_identity),
    plane: CosaAgentPlane = Depends(get_cosa_plane),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> dict[str, Any]:
    """Lấy chi tiết một skill theo ID."""
    ws_id = (
        workspace_id
        or (identity.workspace_id if identity else None)
        or "default_workspace"
    )

    # 1. Spec registry
    if version:
        record = await plane.spec_registry.get("skill", skill_id, version)
        if record is not None:
            return {
                "id": record.spec_id,
                "version": record.version,
                "definition_hash": record.definition_hash,
                "status": record.status,
                **record.content,
            }
    else:
        versions = await plane.spec_registry.list_versions("skill", skill_id)
        if versions:
            latest = versions[-1]
            return {
                "id": latest.spec_id,
                "version": latest.version,
                "definition_hash": latest.definition_hash,
                "status": latest.status,
                **latest.content,
            }

    # 2. Candidate store
    cand = await candidate_store.get_candidate(ws_id, skill_id)
    if cand is not None:
        return {
            "id": cand.proposed_skill.id,
            "candidate_id": cand.candidate_id,
            "version": cand.proposed_skill.version,
            "status": cand.status.value,
            "eval_score": cand.eval_score,
            **cand.proposed_skill.model_dump(mode="json"),
        }

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Skill '{skill_id}' không tồn tại",
    )


@router.put("/{skill_id}")
async def update_skill(
    skill_id: str,
    body: dict[str, Any],
    request: Request,
    identity: Optional[AuthenticatedIdentity] = Depends(get_authenticated_identity),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> dict[str, Any]:
    """Cập nhật metadata hoặc SOP của một candidate skill."""
    ws_id = (identity.workspace_id if identity else None) or "default_workspace"
    cand = await candidate_store.get_candidate(ws_id, skill_id)
    if cand is not None:
        if "name" in body and body["name"]:
            cand.proposed_skill.name = body["name"]
        if "description" in body and body["description"] is not None:
            cand.proposed_skill.description = body["description"]
        if "instructions" in body and body["instructions"]:
            cand.proposed_skill.instructions = body["instructions"]
        if "domain" in body and body["domain"]:
            cand.proposed_skill.applicability["domain"] = body["domain"]
        if "tool_permissions" in body and isinstance(body["tool_permissions"], list):
            cand.proposed_skill.required_capabilities = body["tool_permissions"]
        if "required_capabilities" in body and isinstance(body["required_capabilities"], list):
            cand.proposed_skill.required_capabilities = body["required_capabilities"]
        if "version" in body and body["version"]:
            cand.proposed_skill.version = body["version"]
        cand.proposed_skill.definition_hash = cand.proposed_skill.compute_hash()
        await candidate_store.save_candidate(ws_id, cand)
        return {
            "id": cand.proposed_skill.id,
            "candidate_id": cand.candidate_id,
            **cand.proposed_skill.model_dump(mode="json"),
        }

    return {"id": skill_id, **body}


def create_skill_registry_router() -> APIRouter:
    """Factory trả router đăng ký skill registry."""
    return router
