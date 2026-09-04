"""Workforce API Routes for COSA Agent Platform."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from agent.workforce.catalog import FUNCTIONAL_AGENT_CATALOG, build_functional_spec
from agent.workforce.repository import WorkforceRepository, WorkforceScheduleRecord
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from apps.cosa.api.mvp_response import MvpSourceRef, MvpSuccess, mvp_item, mvp_list
from apps.cosa.api.workforce_schemas import (
    ApprovalDecisionRequest,
    CreateAssignmentRequest,
    CreateScheduleRequest,
    RunScheduleNowOut,
    ScheduleOut,
    WorkforceAssignmentOut,
    WorkforceCapabilityOut,
    WorkforceCompositionEntry,
    WorkforceCostObservationOut,
    WorkforceExceptionListOut,
    WorkforceExceptionOut,
    WorkforceHealthOut,
    WorkforceOrgChartNode,
    WorkforceOrgChartOut,
    WorkforceRosterEntryOut,
    WorkforceRunArtifactOut,
    WorkforceRunDetailOut,
    WorkforceRunEventOut,
    WorkforceRunSummaryOut,
    WorkforceStageRosterEntryOut,
    WorkforceStageRosterOut,
    WorkforceStageRosterStageOut,
    WorkforceStageRosterSummaryOut,
    WorkforceWorkProductOut,
    _ARTIFACT_STATUS_MAP,
)
from apps.cosa.auth.dependency import (
    AuthenticatedIdentity,
    get_authenticated_identity,
    require_workspace_operator,
)
from apps.cosa.auth.jwt import MissingPlatformIdentityError
from apps.cosa.composition.agent_plane import CosaAgentPlane

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent/workforce", tags=["workforce"])


def _get_plane(request: Request) -> CosaAgentPlane:
    plane = getattr(request.app.state, "plane", None) or getattr(
        request.app.state, "cosa_agent_plane", None
    )
    if plane is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CosaAgentPlane is not initialized",
        )
    return plane


def _get_workforce_repo(request: Request) -> WorkforceRepository:
    plane = _get_plane(request)
    if plane.workforce_repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WorkforceRepository is not configured",
        )
    return plane.workforce_repository


async def _fetch_company_stage_roster(
    workspace_id: str, stage_code: str, principal: str
) -> dict:
    import httpx

    from apps.cosa.auth.jwt import mint_company_delegation
    from apps.cosa.config.service_identity import require_internal_url

    company_base_url = require_internal_url(
        "COMPANY_SERVICE_URL", purpose="stage roster proxy", default_dev="http://127.0.0.1:4000"
    )
    token = mint_company_delegation(
        sub=principal,
        workspace_id=workspace_id,
        run_id=f"stage_roster_{workspace_id}_{stage_code}",
        capability_ids=["operations.task.list"],
    )
    url = f"{company_base_url}/operations/tasks/stage-roster/{stage_code}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": workspace_id},
        )
        resp.raise_for_status()
        return resp.json()


# ─── Assignments ───


@router.get("/assignments")
async def list_assignments(
    request: Request,
    status_filter: str | None = Query(None, alias="status"),
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[WorkforceAssignmentOut]]:
    repo = _get_workforce_repo(request)
    records = await repo.list_assignments(identity.workspace_id, status=status_filter)
    items = [
        WorkforceAssignmentOut(
            assignment_id=str(r.assignment_id),
            workspace_id=r.workspace_id,
            functional_key=r.functional_key,
            spec_id=r.spec_id,
            spec_version=r.spec_version,
            definition_hash=r.definition_hash,
            reports_to_assignment_id=str(r.reports_to_assignment_id)
            if r.reports_to_assignment_id
            else None,
            configured_by=r.configured_by,
            status=r.status,
            created_at=r.created_at.isoformat(),
            retired_at=r.retired_at.isoformat() if r.retired_at else None,
        )
        for r in records
    ]
    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="agent.workforce_assignments")])


@router.post("/assignments")
async def create_assignment(
    req: CreateAssignmentRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[WorkforceAssignmentOut]:
    require_workspace_operator(identity)
    repo = _get_workforce_repo(request)

    cat_entry = FUNCTIONAL_AGENT_CATALOG.get(req.functional_key)
    if cat_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Functional key '{req.functional_key}' not found in catalog",
        )

    # Build / resolve the published spec server-side
    spec = build_functional_spec(req.functional_key)
    spec_with_hash = spec.with_hash()

    rec = await repo.create_assignment(
        workspace_id=identity.workspace_id,
        functional_key=req.functional_key,
        spec_id=spec_with_hash.id,
        spec_version=spec_with_hash.version,
        definition_hash=spec_with_hash.definition_hash or "",
        reports_to_assignment_id=req.reports_to_assignment_id,
        configured_by=identity.principal_id,
    )

    out = WorkforceAssignmentOut(
        assignment_id=str(rec.assignment_id),
        workspace_id=rec.workspace_id,
        functional_key=rec.functional_key,
        spec_id=rec.spec_id,
        spec_version=rec.spec_version,
        definition_hash=rec.definition_hash,
        reports_to_assignment_id=str(rec.reports_to_assignment_id)
        if rec.reports_to_assignment_id
        else None,
        configured_by=rec.configured_by,
        status=rec.status,
        created_at=rec.created_at.isoformat(),
        retired_at=rec.retired_at.isoformat() if rec.retired_at else None,
    )
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="agent.workforce_assignments")])


@router.post("/assignments/{assignment_id}/retire")
async def retire_assignment(
    assignment_id: str,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[WorkforceAssignmentOut]:
    require_workspace_operator(identity)
    repo = _get_workforce_repo(request)

    rec = await repo.retire_assignment(
        workspace_id=identity.workspace_id,
        assignment_id=assignment_id,
    )
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment '{assignment_id}' not found in workspace",
        )

    out = WorkforceAssignmentOut(
        assignment_id=str(rec.assignment_id),
        workspace_id=rec.workspace_id,
        functional_key=rec.functional_key,
        spec_id=rec.spec_id,
        spec_version=rec.spec_version,
        definition_hash=rec.definition_hash,
        reports_to_assignment_id=str(rec.reports_to_assignment_id)
        if rec.reports_to_assignment_id
        else None,
        configured_by=rec.configured_by,
        status=rec.status,
        created_at=rec.created_at.isoformat(),
        retired_at=rec.retired_at.isoformat() if rec.retired_at else None,
    )
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="agent.workforce_assignments")])


# ─── Composition & Catalog ───


@router.get("/composition")
async def get_composition(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[WorkforceCompositionEntry]]:
    repo = _get_workforce_repo(request)
    assignments = await repo.list_assignments(identity.workspace_id, status="ACTIVE")
    assignment_map = {a.functional_key: a for a in assignments}

    entries = []
    for key, entry in FUNCTIONAL_AGENT_CATALOG.items():
        spec = build_functional_spec(key).with_hash()
        assigned_record = assignment_map.get(key)
        assigned = assigned_record is not None

        entries.append(
            WorkforceCompositionEntry(
                functional_key=key,
                title=entry.title,
                description=entry.description,
                spec_id=spec.id,
                spec_version=spec.version,
                definition_hash=spec.definition_hash or "",
                allowed_capability_prefixes=list(entry.allowed_capability_prefixes),
                assigned=assigned,
                assignment_id=str(assigned_record.assignment_id) if assigned_record else None,
                status=assigned_record.status if assigned_record else None,
                eligibility_reasons=["eligible" if not assigned else "already_assigned"],
            )
        )
    return mvp_list(entries, [MvpSourceRef(kind="agent_db", ref="agent.workforce_assignments")])


@router.get("/roster")
async def get_roster(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[WorkforceRosterEntryOut]]:
    """Danh sách functional agent thật (không phải `default12Agents` hard-code
    ở FE) — nguồn = FUNCTIONAL_AGENT_CATALOG + trạng thái assignment thật theo
    workspace. Xem docs/superpowers/specs/2026-09-04-workforce-dashboard-backend-gaps-design.md
    Phase 1 cho lý do dùng catalog này thay vì AgentSpec thô."""
    repo = _get_workforce_repo(request)
    assignments = await repo.list_assignments(identity.workspace_id, status="ACTIVE")
    assigned_keys = {a.functional_key for a in assignments}

    entries = [
        WorkforceRosterEntryOut(
            id=idx,
            key=entry.functional_key,
            name=entry.title,
            role_title=entry.description,
            department=entry.default_department,
            agent_type="specialist",
            default_model_profile="reasoning",
            # Hằng số — FunctionalAgentEntry chưa có autonomy_level; mọi entry
            # catalog hiện tại đều dạng "đề xuất, không tự thực thi" (medium).
            risk_level=2,
            status="active" if entry.functional_key in assigned_keys else "available",
            enabled=True,
        )
        for idx, entry in enumerate(FUNCTIONAL_AGENT_CATALOG.values(), start=1)
    ]
    return mvp_list(entries, [MvpSourceRef(kind="agent_db", ref="agent.workforce_assignments")])


@router.get("/artifacts")
async def list_work_products(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[WorkforceWorkProductOut]]:
    """MVP "work products" = artifact ghi nhận trong workspace, workspace-wide
    (khác /runs/{run_id}/artifacts vốn theo từng run). Xem spec Phase 2 cho
    known gap (content_markdown chưa fetch được — FE dùng object_ref)."""
    plane = _get_plane(request)
    if plane.artifact_repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ArtifactRepository is not configured",
        )
    artifacts = await plane.artifact_repository.list_for_workspace(
        identity.workspace_id, limit=limit
    )
    runs = await plane.repository.list_runs(identity.workspace_id, limit=limit)
    run_author_map = {r.run_id: r.root_executable_id for r in runs}

    items = [
        WorkforceWorkProductOut(
            id=a.artifact_id,
            title=a.display_name,
            product_type=a.media_type,
            status=_ARTIFACT_STATUS_MAP.get(a.status, a.status.upper()),
            author_agent_key=run_author_map.get(a.run_id or "", "unknown"),
            object_ref=a.object_ref,
            created_at=a.created_at.isoformat(),
        )
        for a in artifacts
    ]
    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="agent_artifact.workspace_artifacts")])


@router.get("/exceptions")
async def list_exceptions(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[WorkforceExceptionListOut]:
    """MVP read-only "escalations" — KHÔNG có resolve endpoint (xem spec Phase 5).
    Định nghĩa "escalation" = run FAILED trong workspace. tier LUÔN
    "LEAD_NOTIFY" (chưa có phân loại rủi ro FOUNDER_GATE thật — không tự bịa,
    cần thiết kế domain riêng trước khi phân loại rủi ro cao/thấp)."""
    plane = _get_plane(request)
    runs = await plane.repository.list_runs(identity.workspace_id, limit=200)
    from agent.contracts.run import RunStatus

    failed = [r for r in runs if r.status == RunStatus.FAILED]

    items = [
        WorkforceExceptionOut(
            id=r.run_id,
            exception_type="run_failed",
            tier="LEAD_NOTIFY",
            status="OPEN",
            agent_key=r.root_executable_id,
            created_at=r.created_at.isoformat() if r.created_at else datetime.now(UTC).isoformat(),
        )
        for r in failed
    ]
    out = WorkforceExceptionListOut(
        total=len(items),
        founder_gate_count=0,
        lead_notify_count=len(items),
        has_critical=False,
        escalations=items,
    )
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="agent.runs")])


@router.get("/stage-roster/{stage_code}")
async def get_stage_roster(
    stage_code: str,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[WorkforceStageRosterOut]:
    raw = await _fetch_company_stage_roster(
        identity.workspace_id, stage_code, identity.principal_id
    )
    out = WorkforceStageRosterOut(
        stage=WorkforceStageRosterStageOut(
            stage_code=raw["stage"]["stageCode"], task_count=raw["stage"]["taskCount"]
        ),
        roster=[
            WorkforceStageRosterEntryOut(
                task_id=r["taskId"],
                title=r["title"],
                priority=r["priority"],
                status=r["status"],
                project_id=r["projectId"],
            )
            for r in raw["roster"]
        ],
        summary=WorkforceStageRosterSummaryOut(
            total=raw["summary"]["total"],
            high_priority=raw["summary"]["highPriority"],
            medium=raw["summary"]["medium"],
            locked=raw["summary"]["locked"],
        ),
    )
    return mvp_item(out, [MvpSourceRef(kind="company_db", ref="operating.tasks")])


# ─── Org Chart ───


@router.get("/org-chart")
async def get_org_chart(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[WorkforceOrgChartOut]:
    repo = _get_workforce_repo(request)
    active_assignments = await repo.list_assignments(identity.workspace_id, status="ACTIVE")

    node_map = {
        str(a.assignment_id): WorkforceOrgChartNode(
            assignment_id=str(a.assignment_id),
            functional_key=a.functional_key,
            spec_id=a.spec_id,
            status=a.status,
            reports_to_assignment_id=str(a.reports_to_assignment_id)
            if a.reports_to_assignment_id
            else None,
            direct_reports=[],
        )
        for a in active_assignments
    }

    roots: list[WorkforceOrgChartNode] = []
    for node in node_map.values():
        if node.reports_to_assignment_id and node.reports_to_assignment_id in node_map:
            node_map[node.reports_to_assignment_id].direct_reports.append(node)
        else:
            roots.append(node)

    out = WorkforceOrgChartOut(roots=roots, total_assignments=len(active_assignments))
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="agent.workforce_assignments")])


# ─── Capabilities ───


@router.get("/capabilities")
async def list_capabilities(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[WorkforceCapabilityOut]]:
    repo = _get_workforce_repo(request)
    assignments = await repo.list_assignments(identity.workspace_id, status="ACTIVE")

    caps: list[WorkforceCapabilityOut] = []
    seen = set()
    for a in assignments:
        entry = FUNCTIONAL_AGENT_CATALOG.get(a.functional_key)
        if entry:
            for pref in entry.allowed_capability_prefixes:
                if (a.functional_key, pref) not in seen:
                    seen.add((a.functional_key, pref))
                    caps.append(
                        WorkforceCapabilityOut(
                            capability_ref=pref,
                            functional_key=a.functional_key,
                            spec_id=a.spec_id,
                            spec_version=a.spec_version,
                            status="ENABLED",
                        )
                    )

    return mvp_list(caps, [MvpSourceRef(kind="agent_db", ref="agent.workforce_assignments")])


# ─── Cost Observations ───


@router.get("/cost-observations")
async def list_cost_observations(
    request: Request,
    run_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[WorkforceCostObservationOut]]:
    repo = _get_workforce_repo(request)
    records = await repo.list_cost_observations(identity.workspace_id, run_id=run_id, limit=limit)
    items = [
        WorkforceCostObservationOut(
            observation_id=str(r.observation_id),
            workspace_id=r.workspace_id,
            run_id=r.run_id,
            provider_key=r.provider_key,
            model_key=r.model_key,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
            cost_amount=float(r.cost_amount) if r.cost_amount is not None else None,
            currency=r.currency,
            observed_at=r.observed_at.isoformat(),
        )
        for r in records
    ]
    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="agent.run_cost_observations")])


# ─── Health ───


@router.get("/health")
async def get_health(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[WorkforceHealthOut]]:
    plane = _get_plane(request)
    repo = _get_workforce_repo(request)
    assignments = await repo.list_assignments(identity.workspace_id, status="ACTIVE")

    items: list[WorkforceHealthOut] = []
    for a in assignments:
        # Check last run for this spec/assignment if available
        runs = await plane.repository.list_runs(workspace_id=identity.workspace_id, limit=10)
        matching_runs = [r for r in runs if r.root_executable_id == a.spec_id]
        if not matching_runs:
            items.append(
                WorkforceHealthOut(
                    assignment_id=str(a.assignment_id),
                    functional_key=a.functional_key,
                    status="not_observed",
                    observed_at=None,
                    source_ref=None,
                    last_run_id=None,
                    message="Chưa có quan sát chạy/heartbeat",
                )
            )
        else:
            last_run = matching_runs[0]
            status_str = "healthy"
            if last_run.status in ("failed", "cancelled"):
                status_str = "failed"
            elif last_run.status == "waiting_approval":
                status_str = "degraded"

            items.append(
                WorkforceHealthOut(
                    assignment_id=str(a.assignment_id),
                    functional_key=a.functional_key,
                    status=status_str,  # type: ignore[arg-type]
                    observed_at=last_run.created_at.isoformat() if last_run.created_at else None,
                    source_ref=f"agent.runs:{last_run.run_id}",
                    last_run_id=last_run.run_id,
                    message=f"Last run {last_run.run_id} status: {last_run.status}",
                )
            )

    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="agent.workforce_assignments")])


# ─── Runs ───


@router.get("/runs")
async def list_runs(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[WorkforceRunSummaryOut]]:
    plane = _get_plane(request)
    runs = await plane.repository.list_runs(workspace_id=identity.workspace_id, limit=limit)
    items = [
        WorkforceRunSummaryOut(
            run_id=r.run_id,
            workspace_id=r.workspace_id or identity.workspace_id,
            agent_spec_id=r.root_executable_id,
            agent_spec_version=r.root_executable_version,
            definition_hash=r.root_definition_hash or "",
            status=r.status.value if hasattr(r.status, "value") else str(r.status),
            created_at=r.created_at.isoformat() if r.created_at else datetime.now(UTC).isoformat(),
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
            total_tokens=getattr(r, "total_tokens", None),
            error_message=getattr(r, "error_message", None),
        )
        for r in runs
    ]
    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="agent.runs")])


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[WorkforceRunDetailOut]:
    plane = _get_plane(request)
    r = await plane.repository.get_scoped_run(run_id=run_id, workspace_id=identity.workspace_id)
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found in workspace",
        )

    out = WorkforceRunDetailOut(
        run_id=r.run_id,
        workspace_id=r.workspace_id or identity.workspace_id,
        agent_spec_id=r.root_executable_id,
        agent_spec_version=r.root_executable_version,
        definition_hash=r.root_definition_hash or "",
        status=r.status.value if hasattr(r.status, "value") else str(r.status),
        created_at=r.created_at.isoformat() if r.created_at else datetime.now(UTC).isoformat(),
        completed_at=r.completed_at.isoformat() if r.completed_at else None,
        input_payload=r.input_payload if isinstance(r.input_payload, dict) else {},
        output_payload=r.final_output
        if isinstance(r.final_output, dict)
        else ({"result": r.final_output} if r.final_output is not None else None),
        error_message=getattr(r, "error_message", None),
    )
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="agent.runs")])


@router.get("/runs/{run_id}/events")
async def get_run_events(
    run_id: str,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[WorkforceRunEventOut]]:
    plane = _get_plane(request)
    r = await plane.repository.get_scoped_run(run_id=run_id, workspace_id=identity.workspace_id)
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found in workspace",
        )

    events = await plane.stream_event_repository.list_since(run_id)
    items = [
        WorkforceRunEventOut(
            event_id=str(e.event_id) if hasattr(e, "event_id") else f"evt_{idx}",
            run_id=run_id,
            sequence=int(e.sequence) if hasattr(e, "sequence") and e.sequence is not None else idx,
            event_type=e.event_type if hasattr(e, "event_type") else "message",
            payload=e.payload if hasattr(e, "payload") and isinstance(e.payload, dict) else {},
            created_at=e.created_at.isoformat()
            if hasattr(e, "created_at") and e.created_at
            else datetime.now(UTC).isoformat(),
        )
        for idx, e in enumerate(events)
    ]
    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="agent.run_stream_events")])


@router.get("/runs/{run_id}/artifacts")
async def get_run_artifacts(
    run_id: str,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[WorkforceRunArtifactOut]]:
    plane = _get_plane(request)
    r = await plane.repository.get_scoped_run(run_id=run_id, workspace_id=identity.workspace_id)
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found in workspace",
        )

    artifacts = []
    if plane.artifact_repository is not None and r.conversation_id:
        artifacts = await plane.artifact_repository.list_for_conversation(
            identity.workspace_id, r.conversation_id
        )

    items = [
        WorkforceRunArtifactOut(
            artifact_id=str(a.artifact_id),
            run_id=run_id,
            artifact_type=getattr(a, "artifact_type", "document"),
            uri=getattr(a, "uri", f"artifact://{a.artifact_id}"),
            created_at=a.created_at.isoformat()
            if hasattr(a, "created_at") and a.created_at
            else datetime.now(UTC).isoformat(),
        )
        for a in artifacts
    ]
    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="agent.workspace_artifacts")])


# ─── Schedules ───
#
# functional_key + cron_expression: lịch chạy định kỳ cho 1 AI worker trong
# Workforce org-chart — KHÔNG cùng mô hình với /agent/schedules* (đọc
# apps/cosa/api/schedule_routes.py — model agent_profile + hour/minute/
# weekdays, proxy sang services/cosa control-plane, đã có cron dispatcher
# thật). Persist thật từ migration 025_workforce_schedules.sql, nhưng
# thực thi (run-now / cron trigger tự động) CHƯA được hỗ trợ: functional_key
# chưa nối vào execution runtime thật (packages/agent/workforce/catalog.py —
# xem ghi chú "Không đưa vào phạm vi" trong spec điều chỉnh Agent Platform).


def _to_schedule_out(rec: WorkforceScheduleRecord) -> ScheduleOut:
    return ScheduleOut(
        schedule_id=str(rec.schedule_id),
        workspace_id=rec.workspace_id,
        name=rec.name,
        functional_key=rec.functional_key,
        cron_expression=rec.cron_expression,
        status=rec.status,
        next_run_at=None,
        created_at=rec.created_at.isoformat(),
    )


@router.get("/schedules")
async def list_schedules(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[ScheduleOut]]:
    repo = _get_workforce_repo(request)
    records = await repo.list_schedules(identity.workspace_id)
    items = [_to_schedule_out(r) for r in records]
    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="agent.workforce_schedules")])


@router.post("/schedules")
async def create_schedule(
    req: CreateScheduleRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[ScheduleOut]:
    require_workspace_operator(identity)

    if req.functional_key not in FUNCTIONAL_AGENT_CATALOG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Functional key '{req.functional_key}' not found in catalog",
        )

    repo = _get_workforce_repo(request)
    rec = await repo.create_schedule(
        workspace_id=identity.workspace_id,
        name=req.name,
        functional_key=req.functional_key,
        cron_expression=req.cron_expression,
        input_payload=req.input_payload,
        configured_by=identity.principal_id,
    )
    return mvp_item(
        _to_schedule_out(rec), [MvpSourceRef(kind="agent_db", ref="agent.workforce_schedules")]
    )


@router.post("/schedules/{schedule_id}/run-now")
async def run_schedule_now(
    schedule_id: str,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[RunScheduleNowOut]:
    require_workspace_operator(identity)
    repo = _get_workforce_repo(request)

    rec = await repo.get_schedule(identity.workspace_id, schedule_id)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found in workspace",
        )

    # Thực thi thật (dispatch 1 run cho functional_key) chưa được hỗ trợ —
    # functional_key chưa nối vào execution runtime (không có AgentSpec nào
    # được resolve/dispatch cho catalog entry này). Trả lỗi rõ ràng thay vì
    # giả vờ đã QUEUED một run không hề tồn tại.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Workforce schedule execution chưa được hỗ trợ: functional_key "
            f"'{rec.functional_key}' chưa nối vào execution runtime thật."
        ),
    )


# ─── Approvals (Consolidated Canonical Endpoints) ───


@router.get("/approvals")
async def list_approvals(
    request: Request,
    status_filter: str | None = Query(None, alias="status"),
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[dict]]:
    """List pending approvals — consolidated canonical endpoint at /agent/workforce/approvals."""
    plane = _get_plane(request)
    pending = await plane.approval_service.list_pending_approvals(
        workspace_id=identity.workspace_id,
    )
    items = []
    for app in pending:
        if status_filter and app.status != status_filter:
            continue
        items.append(
            {
                "id": app.approval_id,
                "approval_id": app.approval_id,
                "run_id": app.run_id,
                "tool_call_id": app.tool_call_id,
                "checkpoint_ref": app.checkpoint_ref,
                "action": app.action,
                "subject": app.subject,
                "status": app.status,
                "risk_level": app.requirement.get("risk_level", "medium")
                if isinstance(app.requirement, dict)
                else "medium",
                "required_role": app.requirement.get("role", "admin")
                if isinstance(app.requirement, dict)
                else "admin",
                "policy_id": app.requirement.get("policy_id", "default")
                if isinstance(app.requirement, dict)
                else "default",
                "created_at": app.created_at.isoformat()
                if hasattr(app.created_at, "isoformat")
                else str(app.created_at),
            }
        )
    # Trả về đúng MVP envelope (data/meta) thay vì object thô {items,total} —
    # tránh vi phạm contract chung mà mọi consumer MvpRequestClient đang giả định.
    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="agent.approvals")])


@router.post("/approvals/{approval_id}/decision")
async def decide_approval(
    approval_id: str,
    req: ApprovalDecisionRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[dict]:
    """Decide on approval — consolidated canonical endpoint at /agent/workforce/approvals/{approval_id}/decision."""
    plane = _get_plane(request)
    from agent.capabilities.approval_service import ApprovalAlreadyDecidedError

    from apps.cosa.api.event_stream import get_cosa_event_stream_manager

    stream_mgr = get_cosa_event_stream_manager()

    # Tenant check TRƯỚC khi cho phép quyết định
    existing_approval = await plane.approval_service.get_scoped_approval(
        approval_id=approval_id,
        workspace_id=identity.workspace_id,
    )
    if existing_approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval not found: {approval_id}"
        )

    # Support both boolean approved and decision string "APPROVED"/"REJECTED"
    approved_flag = getattr(req, "approved", None)
    if approved_flag is None:
        decision_str = getattr(req, "decision", "")
        approved_flag = decision_str == "APPROVED"

    try:
        decided = await plane.approval_service.submit_decision(
            approval_id=approval_id,
            reviewer=identity.principal_id,
            approved=approved_flag,
            reason=req.reason or "",
        )
    except ApprovalAlreadyDecidedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if not decided:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval not found: {approval_id}"
        )

    if plane.workforce_repository is not None:
        await plane.workforce_repository.enqueue_runtime_signal(
            workspace_id=identity.workspace_id,
            source_kind="approval",
            source_id=approval_id,
            sequence=1,
            state=decided.status,
            observed_at=decided.decided_at or datetime.now(UTC),
        )

    # Bơm Prometheus approval metric
    try:
        from apps.cosa.observability.metrics import record_approval as _record_approval

        _decision = decided.status or ("approved" if approved_flag else "rejected")
        _wait_sec: float | None = None
        if existing_approval.created_at is not None and decided.decided_at is not None:
            _wait_sec = (decided.decided_at - existing_approval.created_at).total_seconds()
        _record_approval(_decision, wait_duration_sec=_wait_sec)
    except Exception:
        pass

    run_id = decided.run_id
    run_record = await plane.repository.get_scoped_run(
        run_id=run_id,
        workspace_id=identity.workspace_id,
    )
    resume_conversation_id = (
        run_record.conversation_id if run_record and run_record.conversation_id else "unknown"
    )

    await stream_mgr.emit(
        plane.stream_event_repository,
        run_id=run_id,
        conversation_id=resume_conversation_id,
        event_type="approval.resolved",
        payload={
            "approval_id": approval_id,
            "status": decided.status,
            "reviewer": decided.reviewer,
            "reason": decided.reason,
        },
    )

    # Resume kernel if approved. Quyết định approval ĐÃ được ghi nhận hợp lệ ở
    # trên (submit_decision) dù bước schedule dưới đây có thất bại — không để
    # 1 principal chưa từng sync qua platform (thiếu platform identity thật)
    # làm mất luôn bản ghi quyết định đã hợp lệ chỉ vì không mint được
    # delegation để tự động resume.
    if approved_flag and decided.checkpoint_ref:
        try:
            control_plane_delegation_token = identity.mint_control_plane_delegation()
        except MissingPlatformIdentityError:
            logger.exception(
                "cannot auto-resume run %s: principal has no platform identity", run_id
            )
        else:
            await plane.scheduler.schedule(
                target_spec_id="cosa.resume",
                input_payload={
                    "task_type": "resume",
                    "run_id": run_id,
                    "checkpoint_ref": decided.checkpoint_ref,
                    "conversation_id": resume_conversation_id,
                    "workspace_id": run_record.workspace_id if run_record else None,
                    "delegation_token": control_plane_delegation_token,
                },
            )

    # Cùng lý do với list_approvals — bọc qua mvp_item để consumer dùng chung
    # MvpRequestClient (đòi hỏi envelope {data, meta}) decode được.
    return mvp_item(
        {
            "approval_id": decided.approval_id,
            "run_id": decided.run_id,
            "status": decided.status,
            "reviewer": decided.reviewer or identity.principal_id,
            "reason": decided.reason,
            "decided_at": (decided.decided_at or datetime.now(UTC)).isoformat(),
        },
        [MvpSourceRef(kind="agent_db", ref="agent.approvals")],
    )
