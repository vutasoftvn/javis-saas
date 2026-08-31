from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from agent.registry.repository import SpecVersionHashConflictError
from agent.skills.candidate_store import (
    InMemorySkillCandidateStore,
    PostgresSkillCandidateStore,
    SkillCandidateStore,
    SkillFeedbackRecord,
)
from agent.skills.contracts import (
    LifecycleApplicability,
    ProjectLifecycleStage,
    SkillCandidate,
    SkillSpec,
    SkillStatus,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from apps.cosa.agents.skillpack_seed import (
    BuiltinSkillpackSeedError,
    seed_builtin_skillpacks,
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
from apps.cosa.auth import (
    AuthenticatedIdentity,
    get_authenticated_identity,
    require_workspace_operator,
    resolve_identity_workspace,
)
from apps.cosa.composition.agent_plane import CosaAgentPlane

logger = logging.getLogger("cosa.api.skill_registry")

__all__ = ["create_skill_registry_router", "router"]

router = APIRouter(prefix="/agent/skills", tags=["skill-registry"])

# Ranh giới mặc định cho skill workspace_custom (Task 9 Step 2): L0/L1,
# artifact/proposal only — không connector, không money movement, không
# external send, không lifecycle transition.
_WORKSPACE_CUSTOM_ALLOWED_CEILINGS = frozenset({"L0_OBSERVE", "L1_PROPOSE"})
_WORKSPACE_CUSTOM_ALLOWED_SIDE_EFFECTS = frozenset({"R", "A"})
_WORKSPACE_CUSTOM_PROHIBITED_CAPABILITY_TOKENS = (
    "connector",
    "payout",
    "transaction.record",
    "message.send",
    "lifecycle",
    "venture_stage",
)
_WORKSPACE_EVAL_VERSION = "cosa.skill-eval.workspace-custom/v1"
_PROMOTION_EVAL_THRESHOLD = 0.8


def _run_workspace_custom_evaluation(
    candidate: SkillCandidate,
    capability_ids: set[str],
) -> tuple[float, dict[str, Any]]:
    """Chạy policy-contract xác định cho skill workspace_custom.

    Đây KHÔNG phải đánh giá hành vi LLM — chỉ kiểm tra ranh giới governance
    (ceiling, side-effect) và capability (đã đăng ký + nằm trong boundary).
    Trả về (computed_score, report) với timestamp + evaluator version. Mọi
    negative case phải "reject" đúng (skill không vượt ranh giới) thì mới đạt
    điểm vượt ngưỡng EVALUATED."""
    spec = candidate.proposed_skill
    case_results: list[dict[str, Any]] = []
    failures: list[str] = []

    ceiling = spec.autonomy.ceiling
    if ceiling in _WORKSPACE_CUSTOM_ALLOWED_CEILINGS:
        case_results.append(
            {"id": "ceiling-within-boundary", "outcome": "reject", "detail": ceiling}
        )
    else:
        failures.append(f"autonomy.ceiling {ceiling} nằm ngoài ranh giới workspace_custom")
        case_results.append(
            {"id": "ceiling-within-boundary", "outcome": "accept", "detail": ceiling}
        )

    side_effect = spec.autonomy.side_effect_class
    if side_effect in _WORKSPACE_CUSTOM_ALLOWED_SIDE_EFFECTS:
        case_results.append(
            {"id": "side-effect-within-boundary", "outcome": "reject", "detail": side_effect}
        )
    else:
        failures.append(
            f"autonomy.side_effect_class {side_effect} nằm ngoài ranh giới artifact/proposal"
        )
        case_results.append(
            {"id": "side-effect-within-boundary", "outcome": "accept", "detail": side_effect}
        )

    for capability in spec.required_capabilities:
        if capability not in capability_ids:
            failures.append(f"capability {capability} chưa đăng ký trong COSA plane")
            case_results.append(
                {"id": "capability-registered", "outcome": "accept", "detail": capability}
            )
        elif any(token in capability for token in _WORKSPACE_CUSTOM_PROHIBITED_CAPABILITY_TOKENS):
            failures.append(f"capability {capability} vượt ranh giới workspace_custom")
            case_results.append(
                {"id": "capability-within-boundary", "outcome": "accept", "detail": capability}
            )
        else:
            case_results.append(
                {"id": "capability-registered", "outcome": "reject", "detail": capability}
            )

    computed_score = 1.0 if not failures else 0.0
    report = {
        "evaluator_version": _WORKSPACE_EVAL_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
        "case_results": case_results,
        "computed_score": computed_score,
        "failures": failures,
    }
    return computed_score, report


def get_skill_candidate_store(request: Request) -> SkillCandidateStore:
    """Dependency injection helper cho SkillCandidateStore."""
    store = getattr(request.app.state, "skill_candidate_store", None)
    if store is None:
        session_factory = getattr(request.app.state, "session_factory", None) or getattr(
            request.app.state, "db_session_factory", None
        )
        if session_factory is not None:
            store = PostgresSkillCandidateStore(session_factory)
        else:
            store = InMemorySkillCandidateStore()
        request.app.state.skill_candidate_store = store
    return store


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
    domain: str | None = Query(None, description="Lọc theo domain/category"),
    status: str | None = Query(
        None, description="Lọc theo status (published, candidate, retired, etc.)"
    ),
    workspace_id: str | None = Query(None, description="Workspace ID"),
    identity: AuthenticatedIdentity | None = Depends(get_authenticated_identity),
    plane: CosaAgentPlane = Depends(get_cosa_plane),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> list[SkillListItem]:
    """Danh sách kỹ năng trong hệ thống (từ published specs và candidates)."""
    if identity is None:
        raise HTTPException(
            status_code=400,
            detail="Missing required workspace context",
        )
    ws_id = resolve_identity_workspace(identity, workspace_id)
    if not ws_id:
        raise HTTPException(
            status_code=400,
            detail="Missing required workspace context",
        )

    items: list[SkillListItem] = []
    seen_ids: set[str] = set()

    # 1. Published / Retired specs từ SpecRegistryRepository
    records = await plane.spec_registry.list_all(spec_kind="skill")
    for r in records:
        content = r.content or {}
        spec_status = r.status.upper() if r.status else "PUBLISHED"
        refs = content.get("references") or {}
        raw_app = content.get("applicability") or {}
        spec_domain = (
            refs.get("category") or raw_app.get("domain") or content.get("domain") or "general"
        )

        if domain and spec_domain.lower() != domain.lower():
            continue
        if status and spec_status.lower() != status.lower():
            continue

        raw_origin = refs.get("origin")
        if isinstance(raw_origin, dict):
            origin = raw_origin.get("repository") or raw_origin.get("upstream") or str(raw_origin)
        elif raw_origin is not None:
            origin = str(raw_origin)
        else:
            origin = "built-in"

        raw_sha = refs.get("upstream_commit") or refs.get("commit")
        adapted_sha = str(raw_sha) if raw_sha is not None else None

        stages = raw_app.get("project_stages", [])
        project_stages = (
            [s.value if hasattr(s, "value") else str(s) for s in stages]
            if isinstance(stages, list)
            else []
        )

        raw_autonomy = content.get("autonomy") or {}
        raw_evidence = content.get("evidence_requirement") or {}
        raw_quality = content.get("quality") or {}

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
            project_stages=project_stages,
            autonomy_ceiling=raw_autonomy.get("ceiling", "L0_OBSERVE"),
            side_effect_class=raw_autonomy.get("side_effect_class", "R"),
            min_source_refs=raw_evidence.get("min_source_refs", 0),
            eval_suite=raw_quality.get("eval_suite") if raw_quality else None,
        )
        items.append(item)
        seen_ids.add(r.spec_id)

    # 2. Candidates từ CandidateStore (workspace-scoped)
    candidates = await candidate_store.list_candidates(ws_id, status=status)
    for c in candidates:
        cand_skill = c.proposed_skill
        cand_domain = str(cand_skill.references.get("category") or "general")

        if domain and cand_domain.lower() != domain.lower():
            continue

        raw_cand_origin = cand_skill.references.get("origin", "candidate")
        cand_origin = (
            raw_cand_origin.get("repository")
            or raw_cand_origin.get("upstream")
            or str(raw_cand_origin)
            if isinstance(raw_cand_origin, dict)
            else str(raw_cand_origin)
        )

        project_stages = [
            s.value if hasattr(s, "value") else str(s)
            for s in cand_skill.applicability.project_stages
        ]

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
            project_stages=project_stages,
            autonomy_ceiling=cand_skill.autonomy.ceiling,
            side_effect_class=cand_skill.autonomy.side_effect_class,
            min_source_refs=cand_skill.evidence_requirement.min_source_refs,
            eval_suite=cand_skill.quality.eval_suite if cand_skill.quality else None,
        )
        items.append(item)

    return items


@router.post("/sync-built-in", response_model=SyncBuiltInResponse)
async def sync_built_in_skills(
    request: Request,
    workspace_id: str | None = Query(None),
    identity: AuthenticatedIdentity | None = Depends(get_authenticated_identity),
    plane: CosaAgentPlane = Depends(get_cosa_plane),
) -> SyncBuiltInResponse:
    """Đồng bộ và publish có kiểm tra tất cả built-in skillpacks vào SpecRegistry.

    Chạy validate_skillpack_tree trước; nếu 0 violation, publish từng skillpack
    vào SpecRegistryRepository (idempotent theo hash). KHÔNG đụng cap_registry.
    """
    if identity:
        role = (identity.role_id or "").lower()
        if role and role not in {"founder", "co-founder", "admin"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sync built-in skills requires founder or admin privilege (current role: {identity.role_id})",
            )
    try:
        records = await seed_builtin_skillpacks(
            plane.spec_registry,
            capability_ids={spec.id for spec in plane.capability_registry.list_specs()},
        )
    except BuiltinSkillpackSeedError as exc:
        logger.error("Built-in skillpack sync rejected: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SpecVersionHashConflictError as exc:
        logger.error("Built-in skillpack sync version conflict: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    synced_items: list[SyncSkillItem] = []
    for record in records:
        content = record.content or {}
        applicability = content.get("applicability") or {}
        autonomy = content.get("autonomy") or {}
        references = content.get("references") or {}
        project_stages = [
            item.value if hasattr(item, "value") else str(item)
            for item in applicability.get("project_stages", [])
        ]
        synced_items.append(
            SyncSkillItem(
                skill_id=record.spec_id,
                version=record.version,
                definition_hash=record.definition_hash,
                published=True,
                domain=str(references.get("category") or "general"),
                project_stages=project_stages,
                autonomy_ceiling=str(autonomy.get("ceiling") or "L0_OBSERVE"),
                side_effect_class=str(autonomy.get("side_effect_class") or "R"),
            )
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
    identity: AuthenticatedIdentity | None = Depends(get_authenticated_identity),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> dict[str, Any]:
    """Tạo mới một SkillCandidate trong workspace."""
    if identity and req.workspace_id and str(identity.workspace_id) != str(req.workspace_id):
        raise HTTPException(
            status_code=400,
            detail=f"Cross-tenant workspace_id mismatch: identity='{identity.workspace_id}', request='{req.workspace_id}'",
        )
    ws_id = (identity.workspace_id if identity else None) or req.workspace_id
    if not ws_id:
        raise HTTPException(
            status_code=400,
            detail="Missing required workspace context",
        )

    skill_id = re.sub(r"[^a-z0-9_-]", "-", req.name.lower()).strip("-")
    if not skill_id:
        skill_id = f"custom-skill-{uuid.uuid4().hex[:6]}"

    # Đường dẫn công khai chỉ tạo workspace_custom; platform_builtin là thay
    # đổi repo (manifest + code review + image build), không qua endpoint này.
    scope = req.scope or "workspace_custom"
    if scope == "platform_builtin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="platform_builtin phải đi qua repository manifest, code review và image build — không thể tạo qua Founder endpoint",
        )
    if scope != "workspace_custom":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"scope không hợp lệ: '{scope}' (chỉ hỗ trợ workspace_custom)",
        )

    spec = SkillSpec(
        id=skill_id,
        version="0.1.0",
        name=req.name,
        description=req.description,
        instructions=req.instructions,
        applicability=LifecycleApplicability(
            project_stages=[ProjectLifecycleStage.P0_DISCOVERY],
            required_context=req.required_context,
        ),
        required_capabilities=req.required_capabilities or req.tool_permissions,
        references={
            "created_by_agent": req.created_by_agent,
            "category": req.domain,
            "scope": scope,
        },
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
    identity: AuthenticatedIdentity | None = Depends(get_authenticated_identity),
    plane: CosaAgentPlane = Depends(get_cosa_plane),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> EvaluateSkillResponse:
    """Chạy policy-contract xác định và ghi report server-attested cho candidate.

    Caller KHÔNG được truyền eval_score hoặc provenance — server tự chạy các
    negative case (boundary + capability), tính score, và chỉ set EVALUATED khi
    mọi negative case reject đúng."""
    ws_id = identity.workspace_id if identity else None
    if not ws_id:
        raise HTTPException(
            status_code=400,
            detail="Missing required workspace context",
        )
    cand = await candidate_store.get_candidate(ws_id, skill_id)

    if cand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate skill '{skill_id}' không tồn tại trong workspace",
        )

    capability_ids = {spec.id for spec in plane.capability_registry.list_specs()}
    computed_score, report = _run_workspace_custom_evaluation(cand, capability_ids)

    # Lưu report vào evidence_refs (durable) và cập nhật score + status.
    cand.eval_score = computed_score
    cand.evidence_refs.append(f"eval_report:{json.dumps(report, sort_keys=True)}")
    if computed_score >= _PROMOTION_EVAL_THRESHOLD:
        cand.status = SkillStatus.EVALUATED
    await candidate_store.save_candidate(ws_id, cand)

    return EvaluateSkillResponse(
        skill_id=skill_id,
        eval_score=computed_score,
        status=cand.status.value,
        report=report,
    )


@router.post("/{skill_id}/promote")
async def promote_skill(
    skill_id: str,
    req: PromoteSkillRequest,
    request: Request,
    identity: AuthenticatedIdentity | None = Depends(get_authenticated_identity),
    plane: CosaAgentPlane = Depends(get_cosa_plane),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> dict[str, Any]:
    """Phê duyệt và đưa Candidate skill vào sản xuất (Published).

    BẮT BUỘC có approved_by và approval_reason (human approval gate).
    """
    if identity:
        require_workspace_operator(identity)
        approved_by = identity.platform_user_id or identity.principal_id or req.approved_by
    else:
        approved_by = req.approved_by

    if not approved_by or not req.approval_reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="approved_by và approval_reason là bắt buộc để promote skill lên sản xuất",
        )

    ws_id = identity.workspace_id if identity else None
    if not ws_id:
        raise HTTPException(
            status_code=400,
            detail="Missing required workspace context",
        )
    cand = await candidate_store.get_candidate(ws_id, skill_id)

    if cand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy candidate '{skill_id}' trong workspace để promote",
        )

    # Chỉ chấp nhận report server-attested: candidate phải ở trạng thái
    # EVALUATED với score vượt ngưỡng — founder không thể promote bản chưa
    # được server đánh giá (không tự ghi eval_score).
    if cand.status != SkillStatus.EVALUATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Candidate skill '{skill_id}' chưa được server đánh giá (status={cand.status.value}). Chạy /evaluate trước.",
        )
    if cand.eval_score < _PROMOTION_EVAL_THRESHOLD:
        raise HTTPException(
            status_code=400,
            detail=f"Candidate skill '{skill_id}' has eval score {cand.eval_score:.2f} < threshold {_PROMOTION_EVAL_THRESHOLD:.2f}. Must pass evaluation before promotion.",
        )

    # Capability phải nằm trong inventory thật — founder không được promote
    # candidate tham chiếu capability chưa tồn tại.
    capability_ids = {spec.id for spec in plane.capability_registry.list_specs()}
    unknown = [
        cap for cap in cand.proposed_skill.required_capabilities if cap not in capability_ids
    ]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown required capabilities: {', '.join(sorted(unknown))}",
        )

    # Workspace-scoped publication: KHÔNG publish vào shared
    # agent_registry.published_specs — skill chỉ tồn tại trong catalogue của
    # workspace này (Step 4). version do caller chọn (mặc định giữ nguyên).
    spec = cand.proposed_skill.model_copy(deep=True)
    spec.status = SkillStatus.PUBLISHED
    spec.publisher = approved_by
    if req.version:
        spec.version = req.version
    cand.proposed_skill = spec
    await candidate_store.save_candidate(ws_id, cand)

    return {
        "skill_id": spec.id,
        "version": spec.version,
        "status": "PUBLISHED",
        "definition_hash": spec.definition_hash or spec.compute_hash(),
        "approved_by": req.approved_by,
        "approval_reason": req.approval_reason,
        "scope": "workspace_custom",
    }


@router.post("/{skill_id}/deprecate")
async def deprecate_skill(
    skill_id: str,
    req: DeprecateSkillRequest,
    request: Request,
    identity: AuthenticatedIdentity | None = Depends(get_authenticated_identity),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> dict[str, Any]:
    """Chuyển trạng thái Skill sang RETIRED (không xoá bản ghi)."""
    if identity is None:
        raise HTTPException(
            status_code=400,
            detail="Missing required workspace context",
        )
    require_workspace_operator(identity)
    ws_id = identity.workspace_id if identity else None
    if not ws_id:
        raise HTTPException(
            status_code=400,
            detail="Missing required workspace context",
        )

    # Deprecation chỉ retire bản custom của workspace caller — KHÔNG đụng
    # shared registry (built-in platform-wide chỉ retire qua thay đổi repo).
    cand = await candidate_store.get_candidate(ws_id, skill_id)
    if cand is not None:
        await candidate_store.update_candidate_status(
            ws_id, cand.candidate_id, status=SkillStatus.RETIRED
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_id}' không tồn tại trong workspace",
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
    identity: AuthenticatedIdentity | None = Depends(get_authenticated_identity),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> dict[str, Any]:
    """Ghi nhận phản hồi kết quả thực thi kỹ năng."""
    ws_id = identity.workspace_id if identity else None
    if not ws_id:
        raise HTTPException(
            status_code=400,
            detail="Missing required workspace context",
        )

    fb = SkillFeedbackRecord(
        workspace_id=ws_id,
        skill_id=skill_id,
        success=req.success,
        rating=req.rating,
        notes=req.notes,
    )
    saved = await candidate_store.save_feedback(fb)
    agg_score = await candidate_store.compute_aggregate_feedback_score(ws_id, skill_id)
    if agg_score is not None:
        cand = await candidate_store.get_candidate(ws_id, skill_id)
        if cand is not None:
            await candidate_store.update_candidate_status(
                ws_id, cand.candidate_id, status=cand.status, eval_score=agg_score
            )

    return {
        "status": "ok",
        "feedback_id": saved.feedback_id,
        "skill_id": skill_id,
        "aggregate_score": agg_score,
        "recorded": True,
    }


@router.get("/{skill_id}")
async def get_skill(
    skill_id: str,
    version: str | None = Query(None),
    workspace_id: str | None = Query(None),
    identity: AuthenticatedIdentity | None = Depends(get_authenticated_identity),
    plane: CosaAgentPlane = Depends(get_cosa_plane),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> dict[str, Any]:
    """Lấy chi tiết một skill theo ID."""
    if identity is None:
        raise HTTPException(
            status_code=400,
            detail="Missing required workspace context",
        )
    ws_id = resolve_identity_workspace(identity, workspace_id)
    if not ws_id:
        raise HTTPException(
            status_code=400,
            detail="Missing required workspace context",
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
    identity: AuthenticatedIdentity | None = Depends(get_authenticated_identity),
    candidate_store: SkillCandidateStore = Depends(get_skill_candidate_store),
) -> dict[str, Any]:
    """Cập nhật metadata hoặc SOP của một candidate skill."""
    if identity is None:
        raise HTTPException(
            status_code=400,
            detail="Missing required workspace context",
        )
    require_workspace_operator(identity)
    ws_id = identity.workspace_id if identity else None
    if not ws_id:
        raise HTTPException(
            status_code=400,
            detail="Missing required workspace context",
        )
    cand = await candidate_store.get_candidate(ws_id, skill_id)
    if cand is not None:
        if body.get("name"):
            cand.proposed_skill.name = body["name"]
        if "description" in body and body["description"] is not None:
            cand.proposed_skill.description = body["description"]
        if body.get("instructions"):
            cand.proposed_skill.instructions = body["instructions"]
        if body.get("domain"):
            cand.proposed_skill.references["category"] = body["domain"]
        if "tool_permissions" in body and isinstance(body["tool_permissions"], list):
            cand.proposed_skill.required_capabilities = body["tool_permissions"]
        if "required_capabilities" in body and isinstance(body["required_capabilities"], list):
            cand.proposed_skill.required_capabilities = body["required_capabilities"]
        if body.get("version"):
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
