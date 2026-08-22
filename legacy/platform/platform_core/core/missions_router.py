from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from db.session import get_db
from core.auth import get_current_workspace_member
from db.models import WorkspaceMember
from founder_os.outcomes.models import Outcome, OutcomeRun, RunStep, RunEvent, Artifact

from workforce.agents.governance.models import AgentRun, AgentEventRecord, AgentToolCall, AgentApproval
from workforce.agents.orchestration.mission_resume_models import MissionResumeJob
from workforce.agents.orchestration.runtime_session_models import RuntimeSession

router = APIRouter()


def _resume_status_for_mission(db: Session, agent_run_id: Optional[int]) -> Optional[str]:
    if agent_run_id is None:
        return None
    pending = (
        db.query(MissionResumeJob)
        .filter(
            MissionResumeJob.mission_run_id == agent_run_id,
            MissionResumeJob.status.in_(("queued", "claimed")),
        )
        .first()
    )
    return "awaiting_specialist_resume" if pending is not None else None


def _format_mission_summary(
    db: Session,
    outcome_run: Optional[OutcomeRun],
    outcome: Optional[Outcome],
    agent_run: Optional[AgentRun],
    evidence_count: int = 0,
    latest_step_text: Optional[str] = None,
    next_step_text: Optional[str] = None,
) -> Dict[str, Any]:

    mission_id = str(agent_run.id) if agent_run else (str(outcome_run.id) if outcome_run else "")
    title = (outcome.title if outcome and outcome.title else None) or (
        f"Mission: {agent_run.job_type}" if agent_run and agent_run.job_type else "Nhiệm vụ COSA"
    )
    agent = (agent_run.agent_key if agent_run and agent_run.agent_key else "chief_of_staff").replace("_", " ").title()

    raw_status = (agent_run.status if agent_run else (outcome_run.status if outcome_run else "running")).lower()
    if raw_status in ("succeeded", "completed"):
        prog = 100
        step_status = "Đã hoàn thành mục tiêu"
    elif raw_status in ("failed", "cancelled"):
        prog = 100
        step_status = f"Dừng thực thi ({raw_status})"
    elif raw_status in ("waiting_approval", "awaiting_approval"):
        prog = 80
        step_status = "Đang chờ phê duyệt từ Founder"
    elif raw_status == "running":
        prog = 65
        step_status = latest_step_text or "Đang thực thi các bước phối hợp"
    else:
        prog = 30
        step_status = latest_step_text or "Đang chuẩn bị khởi tạo"

    budget_raw = agent_run.budget_jsonb if agent_run and agent_run.budget_jsonb else {}
    max_steps = budget_raw.get("max_steps", 10)
    max_cost = budget_raw.get("max_api_cost_usd", 1.0)
    current_cost = agent_run.estimated_cost if agent_run and agent_run.estimated_cost is not None else 0.0
    budget_status = "exceeded" if (agent_run and agent_run.error_code == "BUDGET_EXCEEDED") else "ok"

    is_stuck = agent_run and agent_run.error_code == "STUCK_LOOP"
    loop_health = {
        "status": "stuck" if is_stuck else "healthy",
        "score": 0 if is_stuck else 100,
        "consecutive_repeats": 5 if is_stuck else 0,
    }

    verification_status = outcome_run.verification_status if outcome_run and outcome_run.verification_status else "UNKNOWN"

    created_at = outcome_run.created_at if outcome_run else (agent_run.started_at if agent_run else datetime.utcnow())
    started_at = outcome_run.started_at if outcome_run else (agent_run.started_at if agent_run else None)
    completed_at = outcome_run.completed_at if outcome_run else (agent_run.finished_at if agent_run else None)

    return {
        "mission_id": mission_id,
        "outcome_id": str(outcome.id) if outcome else None,
        "outcome_run_id": str(outcome_run.id) if outcome_run else None,
        "agent_run_id": str(agent_run.id) if agent_run else None,
        "title": title,
        "agent": agent,
        "status": raw_status,
        "progress_percent": prog,
        "current_step": latest_step_text or step_status,
        "next_step": next_step_text or ("Tổng hợp kết quả & lưu bằng chứng" if raw_status == "running" else ""),
        "budget": {
            "max_steps": max_steps,
            "max_cost_usd": max_cost,
            "current_cost_usd": current_cost,
            "budget_status": budget_status,
        },
        "loop_health": loop_health,
        "evidence_count": evidence_count,
        "verification_status": verification_status,
        "resume_status": _resume_status_for_mission(db, agent_run.id if agent_run else None),
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
        "started_at": started_at.isoformat() if started_at and hasattr(started_at, "isoformat") else (str(started_at) if started_at else None),
        "completed_at": completed_at.isoformat() if completed_at and hasattr(completed_at, "isoformat") else (str(completed_at) if completed_at else None),
    }


@router.get("/workspaces/{workspace_id}/missions")
def list_workspace_missions(
    workspace_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = 50,
    offset: int = 0,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Lấy danh sách Missions hợp nhất từ OutcomeRun và AgentRun cho Workspace."""
    if member.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: member does not belong to this workspace",
        )

    # 1. Query OutcomeRuns scoped to workspace via Outcome
    query = (
        db.query(OutcomeRun, Outcome, AgentRun)
        .join(Outcome, OutcomeRun.outcome_id == Outcome.id)
        .outerjoin(AgentRun, OutcomeRun.agent_run_id == AgentRun.id)
        .filter(Outcome.workspace_id == workspace_id)
    )

    if status_filter:
        s_clean = status_filter.lower().strip()
        query = query.filter(
            or_(
                OutcomeRun.status == s_clean,
                Outcome.status == s_clean,
                AgentRun.status == s_clean,
            )
        )

    runs = query.order_by(desc(OutcomeRun.created_at)).offset(offset).limit(limit).all()

    # 2. Also check standalone AgentRuns without OutcomeRun
    existing_agent_run_ids = {r[2].id for r in runs if r[2] is not None}
    standalone_agent_runs = (
        db.query(AgentRun)
        .filter(
            AgentRun.workspace_id == workspace_id,
            AgentRun.outcome_run_id.is_(None),
        )
        .order_by(desc(AgentRun.started_at))
        .limit(limit)
        .all()
    )
    standalone_agent_runs = [ar for ar in standalone_agent_runs if ar.id not in existing_agent_run_ids]

    results = []
    for outcome_run, outcome, agent_run in runs:
        # Count evidence artifacts
        ev_count = (
            db.query(Artifact)
            .filter(
                or_(
                    Artifact.run_id == outcome_run.id,
                    Artifact.outcome_id == outcome.id,
                )
            )
            .count()
        )
        # Find latest event or step
        latest_event = (
            db.query(AgentEventRecord)
            .filter(AgentEventRecord.run_id == agent_run.id)
            .order_by(desc(AgentEventRecord.sequence))
            .first()
            if agent_run
            else None
        )
        latest_step_text = None
        if latest_event and latest_event.payload_jsonb:
            latest_step_text = (
                latest_event.payload_jsonb.get("task")
                or latest_event.payload_jsonb.get("goal")
                or latest_event.event_type.replace("_", " ").capitalize()
            )

        summary = _format_mission_summary(
            db=db,
            outcome_run=outcome_run,
            outcome=outcome,
            agent_run=agent_run,
            evidence_count=ev_count,
            latest_step_text=latest_step_text,
        )
        results.append(summary)

    for ar in standalone_agent_runs:
        summary = _format_mission_summary(
            db=db,
            outcome_run=None,
            outcome=None,
            agent_run=ar,
            evidence_count=0,
        )
        results.append(summary)

    return {
        "status": "success",
        "total": len(results),
        "data": results,
    }


@router.get("/workspaces/{workspace_id}/missions/{mission_id}")
def get_mission_detail(
    workspace_id: int,
    mission_id: str,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Lấy chi tiết toàn diện của một Mission bao gồm Budget, Loop Health, Evidence, Reality Verification & Timeline."""
    if member.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: member does not belong to this workspace",
        )

    try:
        m_id_int = int(mission_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mission_id: must be a valid Snowflake numeric ID",
        )

    # 1. Find by AgentRun id or OutcomeRun id
    agent_run = db.query(AgentRun).filter(AgentRun.id == m_id_int, AgentRun.workspace_id == workspace_id).first()
    outcome_run = None
    outcome = None

    if agent_run:
        if agent_run.outcome_run_id:
            outcome_run = db.query(OutcomeRun).filter(OutcomeRun.id == agent_run.outcome_run_id).first()
        else:
            outcome_run = db.query(OutcomeRun).filter(OutcomeRun.agent_run_id == agent_run.id).first()
    else:
        outcome_run = db.query(OutcomeRun).filter(OutcomeRun.id == m_id_int).first()
        if outcome_run and outcome_run.agent_run_id:
            agent_run = db.query(AgentRun).filter(AgentRun.id == outcome_run.agent_run_id, AgentRun.workspace_id == workspace_id).first()

    if outcome_run:
        outcome = db.query(Outcome).filter(Outcome.id == outcome_run.outcome_id, Outcome.workspace_id == workspace_id).first()

    if not agent_run and not outcome_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mission not found in this workspace",
        )

    # 2. Timeline from AgentEvents & RunSteps
    timeline = []
    if agent_run:
        events = (
            db.query(AgentEventRecord)
            .filter(AgentEventRecord.run_id == agent_run.id)
            .order_by(AgentEventRecord.sequence.asc())
            .all()
        )
        for ev in events:
            timeline.append({
                "id": str(ev.id),
                "sequence": ev.sequence,
                "event_type": ev.event_type,
                "status": ev.status or "completed",
                "actor": ev.agent_key,
                "timestamp": ev.event_time.isoformat() if hasattr(ev.event_time, "isoformat") else str(ev.event_time),
                "payload": ev.payload_jsonb or {},
            })

    if outcome_run:
        steps = db.query(RunStep).filter(RunStep.run_id == outcome_run.id).order_by(RunStep.created_at.asc()).all()
        for s in steps:
            timeline.append({
                "id": str(s.id),
                "sequence": len(timeline) + 1,
                "event_type": f"step.{s.type}",
                "status": s.status,
                "actor": "executor",
                "timestamp": s.created_at.isoformat() if hasattr(s.created_at, "isoformat") else str(s.created_at),
                "payload": {
                    "expected_output": s.expected_output,
                    "risk_level": s.risk_level,
                    "inputs": s.inputs_jsonb or {},
                },
            })

    # 3. Tool Calls
    tool_calls = []
    if agent_run:
        t_calls = (
            db.query(AgentToolCall)
            .filter(AgentToolCall.run_id == agent_run.id)
            .order_by(AgentToolCall.started_at.asc())
            .all()
        )
        for tc in t_calls:
            tool_calls.append({
                "id": str(tc.id),
                "tool_name": tc.tool_name,
                "status": tc.status,
                "risk_level": tc.risk_level,
                "capability": tc.capability,
                "latency_ms": tc.latency_ms,
                "started_at": tc.started_at.isoformat() if hasattr(tc.started_at, "isoformat") else str(tc.started_at),
                "input_preview": tc.input_jsonb or {},
                "output_preview": tc.output_jsonb or {},
            })

    # 4. Evidence & Artifacts
    artifacts_query = db.query(Artifact).filter(Artifact.workspace_id == workspace_id)
    if outcome_run and outcome:
        artifacts_query = artifacts_query.filter(
            or_(
                Artifact.run_id == outcome_run.id,
                Artifact.outcome_id == outcome.id,
            )
        )
    elif outcome_run:
        artifacts_query = artifacts_query.filter(Artifact.run_id == outcome_run.id)
    elif outcome:
        artifacts_query = artifacts_query.filter(Artifact.outcome_id == outcome.id)
    else:
        artifacts_query = artifacts_query.filter(Artifact.id == 0)  # Empty

    artifacts = artifacts_query.all()
    evidence_list = [
        {
            "id": str(a.id),
            "title": a.title,
            "type": a.type,
            "status": a.status,
            "local_uri": a.local_uri,
            "object_storage_uri": a.object_storage_uri,
            "created_at": a.created_at.isoformat() if hasattr(a.created_at, "isoformat") else str(a.created_at),
        }
        for a in artifacts
    ]

    # 5. Approvals
    approvals = []
    if agent_run:
        apprvs = (
            db.query(AgentApproval)
            .filter(AgentApproval.run_id == agent_run.id)
            .order_by(AgentApproval.requested_at.asc())
            .all()
        )
        for ap in apprvs:
            approvals.append({
                "id": str(ap.id),
                "action_type": ap.action_type,
                "tool_name": ap.tool_name,
                "status": ap.status,
                "risk_level": ap.risk_level,
                "requested_at": ap.requested_at.isoformat() if hasattr(ap.requested_at, "isoformat") else str(ap.requested_at),
                "input_preview": ap.input_preview_jsonb or {},
                "reason": ap.reason,
            })

    # 6. Verification detail & Outcome Certificate
    verification_detail = outcome_run.verification_jsonb if outcome_run and outcome_run.verification_jsonb else {}
    summary = _format_mission_summary(
        db=db,
        outcome_run=outcome_run,
        outcome=outcome,
        agent_run=agent_run,
        evidence_count=len(evidence_list),
    )

    # 7. Runtime sessions (ADK/DeepSeek/Sandbox/Human) — timeline cho founder
    runtime_sessions_list = []
    if agent_run:
        rt_sessions = (
            db.query(RuntimeSession)
            .filter(RuntimeSession.mission_run_id == agent_run.id)
            .order_by(RuntimeSession.created_at.asc())
            .all()
        )
        runtime_sessions_list = [
            {
                "id": str(rs.id),
                "runtime_type": rs.runtime_type,
                "external_session_id": rs.external_session_id,
                "status": rs.status,
                "checkpoint_ref": rs.checkpoint_ref,
                "created_at": rs.created_at.isoformat() if hasattr(rs.created_at, "isoformat") else str(rs.created_at),
                "finished_at": rs.finished_at.isoformat() if rs.finished_at and hasattr(rs.finished_at, "isoformat") else None,
            }
            for rs in rt_sessions
        ]

    return {
        "status": "success",
        "data": {
            **summary,
            "desired_result": outcome.desired_result if outcome else (agent_run.metadata_jsonb.get("goal") if agent_run and agent_run.metadata_jsonb else ""),
            "verification_detail": verification_detail,
            "timeline": timeline,
            "tool_calls": tool_calls,
            "evidence": evidence_list,
            "approvals": approvals,
            "runtime_sessions": runtime_sessions_list,
        },
    }

