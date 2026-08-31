"""Workforce API Routes for COSA Agent Platform."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from agent.workforce.catalog import FUNCTIONAL_AGENT_CATALOG, build_functional_spec
from apps.cosa.api.mvp_response import MvpSourceRef, mvp_item, mvp_list
from apps.cosa.api.workforce_schemas import (
    ApprovalDecisionRequest,
    ApprovalDecisionOut,
    ApprovalOut,
    CreateAssignmentRequest,
    CreateScheduleRequest,
    RunScheduleNowOut,
    ScheduleOut,
    WorkforceAssignmentOut,
    WorkforceCapabilityOut,
    WorkforceCompositionEntry,
    WorkforceCostObservationOut,
    WorkforceHealthOut,
    WorkforceOrgChartNode,
    WorkforceOrgChartOut,
    WorkforceRunArtifactOut,
    WorkforceRunDetailOut,
    WorkforceRunEventOut,
    WorkforceRunSummaryOut,
)
from apps.cosa.auth.dependency import (
    AuthenticatedIdentity,
    get_authenticated_identity,
    require_workspace_operator,
)
from apps.cosa.composition.agent_plane import CosaAgentPlane

router = APIRouter(prefix="/agent/workforce", tags=["workforce"])


def _get_plane(request: Request) -> CosaAgentPlane:
    plane = getattr(request.app.state, "plane", None) or getattr(request.app.state, "cosa_agent_plane", None)
    if plane is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CosaAgentPlane is not initialized",
        )
    return plane


# ─── Assignments ───

@router.get("/assignments")
async def list_assignments(
    request: Request,
    status_filter: str | None = Query(None, alias="status"),
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = _get_plane(request)
    records = await plane.workforce_repository.list_assignments(
        identity.workspace_id, status=status_filter
    )
    items = [
        WorkforceAssignmentOut(
            assignment_id=str(r.assignment_id),
            workspace_id=r.workspace_id,
            functional_key=r.functional_key,
            spec_id=r.spec_id,
            spec_version=r.spec_version,
            definition_hash=r.definition_hash,
            reports_to_assignment_id=str(r.reports_to_assignment_id) if r.reports_to_assignment_id else None,
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
):
    require_workspace_operator(identity)
    plane = _get_plane(request)

    cat_entry = FUNCTIONAL_AGENT_CATALOG.get(req.functional_key)
    if cat_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Functional key '{req.functional_key}' not found in catalog",
        )

    # Build / resolve the published spec server-side
    spec = build_functional_spec(req.functional_key)
    spec_with_hash = spec.with_hash()

    rec = await plane.workforce_repository.create_assignment(
        workspace_id=identity.workspace_id,
        functional_key=req.functional_key,
        spec_id=spec_with_hash.id,
        spec_version=spec_with_hash.version,
        definition_hash=spec_with_hash.definition_hash,
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
        reports_to_assignment_id=str(rec.reports_to_assignment_id) if rec.reports_to_assignment_id else None,
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
):
    require_workspace_operator(identity)
    plane = _get_plane(request)

    rec = await plane.workforce_repository.retire_assignment(
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
        reports_to_assignment_id=str(rec.reports_to_assignment_id) if rec.reports_to_assignment_id else None,
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
):
    plane = _get_plane(request)
    assignments = await plane.workforce_repository.list_assignments(
        identity.workspace_id, status="ACTIVE"
    )
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
                definition_hash=spec.definition_hash,
                allowed_capability_prefixes=list(entry.allowed_capability_prefixes),
                assigned=assigned,
                assignment_id=str(assigned_record.assignment_id) if assigned_record else None,
                status=assigned_record.status if assigned_record else None,
                eligibility_reasons=["eligible" if not assigned else "already_assigned"],
            )
        )
    return mvp_list(entries, [MvpSourceRef(kind="agent_db", ref="agent.workforce_assignments")])


# ─── Org Chart ───

@router.get("/org-chart")
async def get_org_chart(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = _get_plane(request)
    active_assignments = await plane.workforce_repository.list_assignments(
        identity.workspace_id, status="ACTIVE"
    )

    node_map = {
        str(a.assignment_id): WorkforceOrgChartNode(
            assignment_id=str(a.assignment_id),
            functional_key=a.functional_key,
            spec_id=a.spec_id,
            status=a.status,
            reports_to_assignment_id=str(a.reports_to_assignment_id) if a.reports_to_assignment_id else None,
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
):
    plane = _get_plane(request)
    assignments = await plane.workforce_repository.list_assignments(
        identity.workspace_id, status="ACTIVE"
    )

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
):
    plane = _get_plane(request)
    records = await plane.workforce_repository.list_cost_observations(
        identity.workspace_id, run_id=run_id, limit=limit
    )
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
):
    plane = _get_plane(request)
    assignments = await plane.workforce_repository.list_assignments(
        identity.workspace_id, status="ACTIVE"
    )

    items: list[WorkforceHealthOut] = []
    for a in assignments:
        # Check last run for this spec/assignment if available
        runs = await plane.repository.list_runs(workspace_id=identity.workspace_id, limit=10)
        matching_runs = [r for r in runs if r.agent_spec_id == a.spec_id]
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
):
    plane = _get_plane(request)
    runs = await plane.repository.list_runs(workspace_id=identity.workspace_id, limit=limit)
    items = [
        WorkforceRunSummaryOut(
            run_id=r.run_id,
            workspace_id=r.workspace_id or identity.workspace_id,
            agent_spec_id=r.agent_spec_id,
            agent_spec_version=r.agent_spec_version,
            definition_hash=r.definition_hash,
            status=r.status,
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
):
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
        agent_spec_id=r.agent_spec_id,
        agent_spec_version=r.agent_spec_version,
        definition_hash=r.definition_hash,
        status=r.status,
        created_at=r.created_at.isoformat() if r.created_at else datetime.now(UTC).isoformat(),
        completed_at=r.completed_at.isoformat() if r.completed_at else None,
        input_payload=r.input_payload if isinstance(r.input_payload, dict) else {},
        output_payload=r.output_payload if isinstance(r.output_payload, dict) else None,
        error_message=getattr(r, "error_message", None),
    )
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="agent.runs")])


@router.get("/runs/{run_id}/events")
async def get_run_events(
    run_id: str,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = _get_plane(request)
    r = await plane.repository.get_scoped_run(run_id=run_id, workspace_id=identity.workspace_id)
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found in workspace",
        )

    events = await plane.stream_event_repository.list_events(run_id)
    items = [
        WorkforceRunEventOut(
            event_id=str(e.event_id) if hasattr(e, "event_id") else f"evt_{idx}",
            run_id=run_id,
            sequence=e.sequence if hasattr(e, "sequence") else idx,
            event_type=e.event_type if hasattr(e, "event_type") else "message",
            payload=e.payload if hasattr(e, "payload") and isinstance(e.payload, dict) else {},
            created_at=e.created_at.isoformat() if hasattr(e, "created_at") and e.created_at else datetime.now(UTC).isoformat(),
        )
        for idx, e in enumerate(events)
    ]
    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="agent.run_stream_events")])


@router.get("/runs/{run_id}/artifacts")
async def get_run_artifacts(
    run_id: str,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = _get_plane(request)
    r = await plane.repository.get_scoped_run(run_id=run_id, workspace_id=identity.workspace_id)
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found in workspace",
        )

    artifacts = []
    if plane.artifact_repository is not None:
        artifacts = await plane.artifact_repository.list_artifacts(run_id=run_id)

    items = [
        WorkforceRunArtifactOut(
            artifact_id=str(a.artifact_id),
            run_id=run_id,
            artifact_type=getattr(a, "artifact_type", "document"),
            uri=getattr(a, "uri", f"artifact://{a.artifact_id}"),
            created_at=a.created_at.isoformat() if hasattr(a, "created_at") and a.created_at else datetime.now(UTC).isoformat(),
        )
        for a in artifacts
    ]
    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="agent.workspace_artifacts")])


# ─── Schedules ───

@router.get("/schedules")
async def list_schedules(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    # Schedules from workspace scheduler
    items: list[ScheduleOut] = []
    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="agent.schedules")])


@router.post("/schedules")
async def create_schedule(
    req: CreateScheduleRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    require_workspace_operator(identity)
    schedule_id = f"sched_{uuid4().hex[:12]}"
    out = ScheduleOut(
        schedule_id=schedule_id,
        workspace_id=identity.workspace_id,
        name=req.name,
        functional_key=req.functional_key,
        cron_expression=req.cron_expression,
        status="ACTIVE",
        next_run_at=None,
        created_at=datetime.now(UTC).isoformat(),
    )
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="agent.schedules")])


@router.post("/schedules/{schedule_id}/run-now")
async def run_schedule_now(
    schedule_id: str,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    require_workspace_operator(identity)
    run_id = f"run_{uuid4().hex[:12]}"
    out = RunScheduleNowOut(
        schedule_id=schedule_id,
        triggered_run_id=run_id,
        status="QUEUED",
    )
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="agent.schedules")])


# ─── Approvals ───

@router.get("/approvals")
async def list_approvals(
    request: Request,
    status_filter: str | None = Query(None, alias="status"),
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = _get_plane(request)
    pending = await plane.approval_service.list_pending_approvals(
        workspace_id=identity.workspace_id,
    )
    items = [
        ApprovalOut(
            approval_id=app.approval_id,
            workspace_id=identity.workspace_id,
            run_id=app.run_id,
            capability_ref=app.action,
            action_class="B",
            status=app.status,
            requested_at=app.created_at.isoformat() if app.created_at else datetime.now(UTC).isoformat(),
            decided_at=app.decided_at.isoformat() if getattr(app, "decided_at", None) else None,
            decision=getattr(app, "decision", None),
            reason=getattr(app, "reason", None),
        )
        for app in pending
        if status_filter is None or app.status == status_filter
    ]
    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="agent.approvals")])


@router.post("/approvals/{approval_id}/decision")
async def decide_approval(
    approval_id: str,
    req: ApprovalDecisionRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    require_workspace_operator(identity)
    plane = _get_plane(request)

    existing_approval = await plane.approval_service.get_scoped_approval(
        approval_id=approval_id,
        workspace_id=identity.workspace_id,
    )
    if existing_approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval '{approval_id}' not found in workspace",
        )

    approved = req.decision == "APPROVED"
    decided = await plane.approval_service.submit_decision(
        approval_id=approval_id,
        reviewer=identity.principal_id,
        approved=approved,
        reason=req.reason or "",
    )
    if not decided:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval '{approval_id}' could not be updated",
        )

    # Durable Outbox Signal: enqueue runtime signal after durable approval decision
    now = datetime.now(UTC)
    await plane.workforce_repository.enqueue_runtime_signal(
        workspace_id=identity.workspace_id,
        source_kind="approval",
        source_id=approval_id,
        sequence=1,
        state=decided.status,
        observed_at=now,
    )

    out = ApprovalDecisionOut(
        approval_id=decided.approval_id,
        status=decided.status,
        decided_at=decided.decided_at.isoformat() if decided.decided_at else now.isoformat(),
        reason=decided.reason,
    )
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="agent.approvals")])
