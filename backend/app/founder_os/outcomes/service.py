from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep, RunEvent, Artifact
from app.core.audit import write_audit_log


def _emit_run_event_live(
    run_id: int,
    workspace_id: int,
    event_type: str,
    payload: Optional[Dict[str, Any]],
) -> None:
    """Publish a RunEvent onto the live mission event bus (SSE / Mission Inspector / Hologram Hub).

    RunEvent rows are the Mission Ledger's work-item lifecycle events (see missions_router.py).
    They used to be a DB-only insert, so any live subscriber watching mission_control_bus only
    ever saw AgentEventRecord (agent-execution) events from chief_of_staff.py, never these. This
    mirrors that same call convention so both event families reach the same live bus. Additive
    only - the RunEvent DB row is still written by the caller regardless of bus outcome.

    Imported lazily (not at module top level): app.workforce.agents.orchestration eagerly imports
    chief_of_staff.py's whole dependency chain (governance kernel, runtime adapters, tool
    bridge, ...), which has a pre-existing circular import when triggered from this module at
    process-start time via outcomes/router.py -> outcomes/service.py (main.py imports the
    outcomes router before the agents/runtime chain gets a chance to fully initialize itself).
    Deferring the import to call time (well after app startup has finished) sidesteps that
    without having to touch the unrelated governance/runtime import cycle.
    """
    from app.workforce.agents.orchestration.mission_control_bus import mission_control_bus

    mission_control_bus.emit_event(
        run_id=str(run_id),
        workspace_id=str(workspace_id),
        event_type=event_type,
        data=payload or {},
        agent_key="outcome_engine",
    )


def create_outcome(
    db: Session,
    workspace_id: int,
    user_id: int,
    title: str,
    desired_result: str,
    project_id: Optional[int] = None,
    acceptance_criteria: Optional[Dict[str, Any]] = None,
) -> Outcome:
    outcome = Outcome(
        workspace_id=workspace_id,
        project_id=project_id,
        title=title,
        desired_result=desired_result,
        acceptance_criteria=acceptance_criteria,
        requested_by=user_id,
        status="draft",
        created_at=datetime.utcnow(),
    )
    db.add(outcome)
    db.commit()
    db.refresh(outcome)

    write_audit_log(
        db=db,
        actor_type="user",
        actor_id=user_id,
        action="outcome.create",
        target_type="outcome",
        target_id=outcome.id,
        metadata_jsonb={"workspace_id": str(workspace_id), "title": title}
    )
    return outcome


def list_outcomes(
    db: Session,
    workspace_id: int,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Outcome]:
    query = db.query(Outcome).filter(Outcome.workspace_id == workspace_id)
    if status:
        query = query.filter(Outcome.status == status)
    return query.order_by(Outcome.created_at.desc()).offset(offset).limit(limit).all()


def get_outcome(
    db: Session,
    outcome_id: int,
    workspace_id: int,
) -> Optional[Outcome]:
    return db.query(Outcome).filter(
        Outcome.id == outcome_id,
        Outcome.workspace_id == workspace_id
    ).first()


def create_outcome_run(
    db: Session,
    outcome_id: int,
    workspace_id: int,
    user_id: int,
) -> OutcomeRun:
    outcome = get_outcome(db, outcome_id=outcome_id, workspace_id=workspace_id)
    if not outcome:
        raise ValueError("Outcome not found or access denied")

    outcome.status = "running"
    
    run = OutcomeRun(
        outcome_id=outcome_id,
        status="running",
        started_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Initial Run Event
    run_event = RunEvent(
        run_id=run.id,
        event_type="run.created",
        payload_jsonb={"outcome_id": str(outcome_id), "title": outcome.title},
        created_at=datetime.utcnow(),
    )
    db.add(run_event)
    _emit_run_event_live(run.id, workspace_id, run_event.event_type, run_event.payload_jsonb)

    # Initial step execution
    initial_step = RunStep(
        run_id=run.id,
        type="plan_generation",
        inputs_jsonb={"desired_result": outcome.desired_result},
        expected_output="Detailed execution plan and draft artifact",
        risk_level="L0",
        status="completed",
        created_at=datetime.utcnow(),
    )
    db.add(initial_step)
    db.commit()

    # Step completed event
    step_event = RunEvent(
        run_id=run.id,
        event_type="step.completed",
        payload_jsonb={"step_id": str(initial_step.id), "type": initial_step.type},
        created_at=datetime.utcnow(),
    )
    db.add(step_event)
    _emit_run_event_live(run.id, workspace_id, step_event.event_type, step_event.payload_jsonb)

    # Draft Artifact generation
    artifact = Artifact(
        run_id=run.id,
        outcome_id=outcome.id,
        workspace_id=workspace_id,
        type="document",
        title=f"Báo cáo kết quả: {outcome.title}",
        status="draft",
        created_by=user_id,
        created_at=datetime.utcnow(),
    )
    db.add(artifact)
    db.commit()

    # Artifact event
    artifact_event = RunEvent(
        run_id=run.id,
        event_type="artifact.created",
        payload_jsonb={"artifact_id": str(artifact.id), "title": artifact.title, "type": artifact.type},
        created_at=datetime.utcnow(),
    )
    db.add(artifact_event)
    db.commit()
    _emit_run_event_live(run.id, workspace_id, artifact_event.event_type, artifact_event.payload_jsonb)

    write_audit_log(
        db=db,
        actor_type="user",
        actor_id=user_id,
        action="outcome.run.start",
        target_type="outcome_run",
        target_id=run.id,
        metadata_jsonb={"workspace_id": str(workspace_id), "outcome_id": str(outcome_id)}
    )

    return run


def get_run(
    db: Session,
    run_id: int,
    workspace_id: int,
) -> Optional[OutcomeRun]:
    run = db.query(OutcomeRun).join(Outcome).filter(
        OutcomeRun.id == run_id,
        Outcome.workspace_id == workspace_id
    ).first()
    return run


def list_run_events(
    db: Session,
    run_id: int,
    workspace_id: int,
) -> List[RunEvent]:
    run = get_run(db, run_id=run_id, workspace_id=workspace_id)
    if not run:
        return []
    return db.query(RunEvent).filter(RunEvent.run_id == run_id).order_by(RunEvent.created_at.asc()).all()


def create_artifact(
    db: Session,
    workspace_id: int,
    user_id: int,
    type: str,
    title: str,
    run_id: Optional[int] = None,
    outcome_id: Optional[int] = None,
    local_uri: Optional[str] = None,
    object_storage_uri: Optional[str] = None,
    content_hash: Optional[str] = None,
) -> Artifact:
    artifact = Artifact(
        workspace_id=workspace_id,
        run_id=run_id,
        outcome_id=outcome_id,
        type=type,
        title=title,
        local_uri=local_uri,
        object_storage_uri=object_storage_uri,
        content_hash=content_hash,
        status="draft",
        created_by=user_id,
        created_at=datetime.utcnow(),
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)

    write_audit_log(
        db=db,
        actor_type="user",
        actor_id=user_id,
        action="artifact.create",
        target_type="artifact",
        target_id=artifact.id,
        metadata_jsonb={"workspace_id": str(workspace_id), "title": title, "type": type}
    )
    return artifact


def get_artifact(
    db: Session,
    artifact_id: int,
    workspace_id: int,
) -> Optional[Artifact]:
    return db.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.workspace_id == workspace_id
    ).first()


def list_artifacts(
    db: Session,
    workspace_id: int,
    type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Artifact]:
    query = db.query(Artifact).filter(Artifact.workspace_id == workspace_id)
    if type:
        query = query.filter(Artifact.type == type)
    return query.order_by(Artifact.created_at.desc()).offset(offset).limit(limit).all()
