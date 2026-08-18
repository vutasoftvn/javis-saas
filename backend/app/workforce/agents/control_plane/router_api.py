"""Agentic Control Plane Router API.

Provides tenant-scoped CRUD management for Agent Goals, Decomposition Plans, Runs, and Memories.
Mounted under `/api/v1/agent` via `app.workforce.agents.gateway.router`.

Note: Real-time chat intent classification & canonical verb gating are handled by
`app.workforce.chat.conversation_gate`.
"""

from datetime import datetime, timezone
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.core.snowflake import generate_snowflake_id
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.workforce.agents.governance.models import AgentRun, AgentEventRecord
from app.workforce.agents.control_plane.models import AgentGoal, AgentPlan, AgentPlanStep, AgentMemoryItem
from app.workforce.agents.control_plane.context import ContextResolver
from app.workforce.agents.control_plane.planner import ControlPlanePlanner
from app.workforce.agents.control_plane.execution import ControlPlaneExecutionManager
from app.workforce.agents.control_plane.evaluator import PlanEvaluator

router = APIRouter(tags=["agentic-control-plane"])


# --- Schemas ---

class CreateGoalRequest(BaseModel):
    title: str
    description: Optional[str] = None
    goal_type: str = "business_goal"
    target_metric: Optional[dict[str, Any]] = None
    deadline: Optional[datetime] = None
    auto_plan: bool = True
    domain_hint: Optional[str] = None


class CreateMemoryRequest(BaseModel):
    memory_type: str  # company_fact, founder_preference, operating_constraint, approved_decision
    domain: str = "general"
    key: str
    value: dict[str, Any]
    provenance: Optional[dict[str, Any]] = None


# --- Endpoints ---

@router.post("/goals")
async def create_goal(
    req: CreateGoalRequest,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
):
    workspace_id = current_member.workspace_id
    user_id = current_member.user_id

    goal_id = generate_snowflake_id()
    goal = AgentGoal(
        id=goal_id,
        workspace_id=workspace_id,
        company_id=workspace_id,
        user_id=user_id,
        goal_type=req.goal_type,
        title=req.title,
        description=req.description,
        target_metric_jsonb=req.target_metric,
        deadline=req.deadline,
        status="active",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)

    created_plan_id = None
    if req.auto_plan:
        context_envelope = ContextResolver.resolve(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        plan = ControlPlanePlanner.create_plan_for_goal(
            db=db,
            goal=goal,
            context=context_envelope,
            domain_hint=req.domain_hint or "founder",
        )
        created_plan_id = str(plan.id)

    return {
        "id": str(goal.id),
        "id_str": str(goal.id),
        "workspace_id": str(goal.workspace_id),
        "title": goal.title,
        "goal_type": goal.goal_type,
        "status": goal.status,
        "active_plan_id": created_plan_id,
        "created_at": goal.created_at.isoformat(),
    }


@router.get("/goals")
async def list_goals(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
):
    q = db.query(AgentGoal).filter(AgentGoal.workspace_id == current_member.workspace_id)
    if status_filter:
        q = q.filter(AgentGoal.status == status_filter)
    goals = q.order_by(AgentGoal.created_at.desc()).all()

    return [
        {
            "id": str(g.id),
            "id_str": str(g.id),
            "title": g.title,
            "description": g.description,
            "goal_type": g.goal_type,
            "status": g.status,
            "deadline": g.deadline.isoformat() if g.deadline else None,
            "plan_count": len(g.plans),
            "created_at": g.created_at.isoformat(),
        }
        for g in goals
    ]


@router.get("/goals/{goal_id}")
async def get_goal_details(
    goal_id: int,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
):
    goal = db.query(AgentGoal).filter(AgentGoal.id == goal_id, AgentGoal.workspace_id == current_member.workspace_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    return {
        "id": str(goal.id),
        "id_str": str(goal.id),
        "workspace_id": str(goal.workspace_id),
        "title": goal.title,
        "description": goal.description,
        "goal_type": goal.goal_type,
        "status": goal.status,
        "target_metric": goal.target_metric_jsonb,
        "deadline": goal.deadline.isoformat() if goal.deadline else None,
        "plans": [
            {
                "id": str(p.id),
                "id_str": str(p.id),
                "title": p.title,
                "status": p.status,
                "step_count": len(p.steps),
                "created_at": p.created_at.isoformat(),
            }
            for p in goal.plans
        ],
        "created_at": goal.created_at.isoformat(),
    }


@router.post("/goals/{goal_id}/plan")
async def generate_plan_for_goal(
    goal_id: int,
    domain_hint: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
):
    goal = db.query(AgentGoal).filter(AgentGoal.id == goal_id, AgentGoal.workspace_id == current_member.workspace_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    context = ContextResolver.resolve(db=db, workspace_id=current_member.workspace_id, user_id=current_member.user_id)
    plan = ControlPlanePlanner.create_plan_for_goal(
        db=db,
        goal=goal,
        context=context,
        domain_hint=domain_hint or "founder",
    )

    return {
        "plan_id": str(plan.id),
        "goal_id": str(goal.id),
        "title": plan.title,
        "status": plan.status,
        "step_count": len(plan.steps),
    }


@router.get("/plans/{plan_id}")
async def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
):
    plan = db.query(AgentPlan).filter(AgentPlan.id == plan_id, AgentPlan.workspace_id == current_member.workspace_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    evaluation = PlanEvaluator.evaluate_plan(db, plan.id)

    return {
        "id": str(plan.id),
        "id_str": str(plan.id),
        "goal_id": str(plan.goal_id),
        "title": plan.title,
        "rationale": plan.rationale,
        "status": plan.status,
        "version": plan.version,
        "evaluation": evaluation.model_dump(),
        "steps": [
            {
                "id": str(s.id),
                "id_str": str(s.id),
                "sequence_order": s.sequence_order,
                "title": s.title,
                "domain": s.domain,
                "capability": s.capability,
                "tool_id": s.tool_id,
                "policy_level": s.policy_level,
                "status": s.status,
                "approval_id": str(s.approval_id) if s.approval_id else None,
                "output": s.output_jsonb,
            }
            for s in plan.steps
        ],
    }


@router.get("/plans/{plan_id}/events")
async def get_plan_events(
    plan_id: int,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
):
    plan = db.query(AgentPlan).filter(AgentPlan.id == plan_id, AgentPlan.workspace_id == current_member.workspace_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    events = (
        db.query(AgentEventRecord)
        .filter(AgentEventRecord.plan_id == plan_id)
        .order_by(AgentEventRecord.sequence.asc(), AgentEventRecord.event_time.asc())
        .all()
    )

    return [
        {
            "id": str(e.id),
            "id_str": str(e.id),
            "run_id": str(e.run_id) if e.run_id else None,
            "plan_id": str(e.plan_id) if e.plan_id else None,
            "step_id": str(e.step_id) if e.step_id else None,
            "company_id": str(e.company_id) if e.company_id else None,
            "actor_type": e.actor_type,
            "actor_id": e.actor_id,
            "tool_id": e.tool_id,
            "status": e.status,
            "sequence": e.sequence,
            "agent_key": e.agent_key,
            "event_type": e.event_type,
            "event_time": e.event_time.isoformat() if e.event_time else None,
            "payload": e.payload_jsonb,
        }
        for e in events
    ]


@router.post("/plans/{plan_id}/execute-step")
async def execute_plan_step(
    plan_id: int,
    step_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
):
    plan = db.query(AgentPlan).filter(AgentPlan.id == plan_id, AgentPlan.workspace_id == current_member.workspace_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if step_id:
        res = await ControlPlaneExecutionManager.execute_step(
            db=db,
            plan_id=plan.id,
            step_id=step_id,
            user_id=current_member.user_id,
            workspace_id=current_member.workspace_id,
        )
    else:
        res = await ControlPlaneExecutionManager.execute_next_pending_step(
            db=db,
            plan_id=plan.id,
            user_id=current_member.user_id,
            workspace_id=current_member.workspace_id,
        )

    if not res:
        return {"status": "no_pending_steps", "message": "All steps completed or no runnable steps found"}

    eval_result = PlanEvaluator.evaluate_plan(db, plan.id)
    return {
        "step_result": res.model_dump(),
        "plan_evaluation": eval_result.model_dump(),
    }


@router.post("/plans/{plan_id}/approve")
async def approve_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
):
    plan = db.query(AgentPlan).filter(AgentPlan.id == plan_id, AgentPlan.workspace_id == current_member.workspace_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.status = "approved"
    db.commit()
    return {"plan_id": str(plan.id), "status": plan.status}


@router.get("/runs")
async def list_agent_runs(
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
):
    query = db.query(AgentRun).filter(AgentRun.workspace_id == current_member.workspace_id)
    if status:
        query = query.filter(AgentRun.status == status)

    total = query.count()
    runs = query.order_by(AgentRun.started_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": str(r.id),
                "id_str": str(r.id),
                "workspace_id": str(r.workspace_id),
                "company_id": str(r.company_id) if r.company_id else None,
                "user_id": str(r.user_id),
                "agent_key": r.agent_key,
                "runtime": r.runtime,
                "status": r.status,
                "permission_profile": r.permission_profile,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "latency_ms": r.latency_ms,
                "error_code": r.error_code,
                "error_message": r.error_message,
                "metadata": r.metadata_jsonb,
            }
            for r in runs
        ],
    }


@router.get("/runs/{run_id}/events")
async def get_run_events(
    run_id: int,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
):
    events = (
        db.query(AgentEventRecord)
        .filter(AgentEventRecord.run_id == run_id)
        .order_by(AgentEventRecord.event_time.asc())
        .all()
    )

    return [
        {
            "id": str(e.id),
            "run_id": str(e.run_id),
            "sequence": e.sequence,
            "agent_key": e.agent_key,
            "event_type": e.event_type,
            "payload": e.payload_jsonb,
            "timestamp": e.event_time.isoformat() if e.event_time else None,
        }
        for e in events
    ]


@router.post("/memories")
async def create_business_memory(
    req: CreateMemoryRequest,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
):
    workspace_id = current_member.workspace_id
    user_id = current_member.user_id

    mem_id = generate_snowflake_id()
    mem = AgentMemoryItem(
        id=mem_id,
        workspace_id=workspace_id,
        company_id=workspace_id,
        user_id=user_id,
        memory_type=req.memory_type,
        domain=req.domain,
        key=req.key,
        value_jsonb=req.value,
        provenance_jsonb=req.provenance or {"source": "founder_manual_entry"},
        status="active",
    )
    db.add(mem)
    db.commit()
    db.refresh(mem)

    return {
        "id": str(mem.id),
        "key": mem.key,
        "domain": mem.domain,
        "memory_type": mem.memory_type,
        "status": mem.status,
    }


@router.get("/memories")
async def list_business_memories(
    domain: Optional[str] = Query(None),
    memory_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
):
    q = db.query(AgentMemoryItem).filter(AgentMemoryItem.workspace_id == current_member.workspace_id, AgentMemoryItem.status == "active")
    if domain:
        q = q.filter(AgentMemoryItem.domain == domain)
    if memory_type:
        q = q.filter(AgentMemoryItem.memory_type == memory_type)
    items = q.order_by(AgentMemoryItem.created_at.desc()).all()

    return [
        {
            "id": str(m.id),
            "key": m.key,
            "domain": m.domain,
            "memory_type": m.memory_type,
            "value": m.value_jsonb,
            "provenance": m.provenance_jsonb,
            "created_at": m.created_at.isoformat(),
        }
        for m in items
    ]
