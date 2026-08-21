from datetime import datetime, timezone
import json
import os
from typing import Any, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from workforce.agents.governance.models import AgentApproval
from workforce.automation.models import AutomationCallback, AutomationDefinition, AutomationRun
from workforce.automation.runtime.adapters.n8n import verify_hmac_signature
from workforce.automation.runtime.manager import automation_runtime_manager
from workforce.automation.runtime.types import AutomationHealth, AutomationRequest
from core.auth import get_current_workspace_member
from core.snowflake import generate_snowflake_id, generate_snowflake_str
from db.models import WorkspaceMember
from db.session import get_db

router = APIRouter()

_TERMINAL_AUTOMATION_STATUSES = {"succeeded", "completed", "failed", "cancelled"}


class ExecuteAutomationRequest(BaseModel):
    automation_key: str
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None
    agent_run_id: Optional[int] = None
    approval_id: Optional[int] = None


class AutomationRunResponse(BaseModel):
    id: str
    workspace_id: str
    automation_key: str
    provider: str
    provider_execution_id: Optional[str] = None
    status: str
    started_at: str
    finished_at: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    error_summary: Optional[str] = None


def process_n8n_delegation_callback(
    *,
    db: Session,
    data: dict[str, Any],
    signature: str,
) -> dict[str, Any]:
    """Apply one verified n8n callback after durable correlation checks.

    Phase-C delegation runs carry a correlation id in their persisted payload.  Those
    callbacks are rejected unless every routing identity matches the stored run.  Older
    automation callers did not send the Phase-C envelope, so they retain the legacy
    execution-id correlation while all newly delegated work gets the stricter contract.
    """
    exec_id = data.get("execution_id")
    if not exec_id:
        raise HTTPException(status_code=400, detail="Missing execution_id in callback")
    try:
        run_id_int = int(exec_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid execution_id format")

    run = db.query(AutomationRun).filter(AutomationRun.id == run_id_int).first()
    if not run:
        raise HTTPException(status_code=404, detail="AutomationRun not found")

    stored_payload = run.payload_jsonb if isinstance(run.payload_jsonb, dict) else {}
    expected_correlation = stored_payload.get("correlation_id")
    is_delegated = bool(expected_correlation)
    if is_delegated:
        event_key = data.get("event_key")
        if not isinstance(event_key, str) or not event_key:
            raise HTTPException(status_code=400, detail="Missing callback event_key")
        try:
            callback_workspace_id = int(data.get("workspace_id"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=409, detail="Callback workspace correlation mismatch")
        if callback_workspace_id != run.workspace_id:
            raise HTTPException(status_code=409, detail="Callback workspace correlation mismatch")
        if data.get("provider") != run.provider:
            raise HTTPException(status_code=409, detail="Callback provider correlation mismatch")
        if data.get("provider_execution_id") != run.provider_execution_id:
            raise HTTPException(status_code=409, detail="Callback external run correlation mismatch")
        if data.get("correlation_id") != expected_correlation:
            raise HTTPException(status_code=409, detail="Callback correlation_id mismatch")
        replay = (
            db.query(AutomationCallback)
            .filter(
                AutomationCallback.run_id == run.id,
                AutomationCallback.signature == signature,
            )
            .first()
        )
        if replay is not None:
            raise HTTPException(status_code=409, detail="Callback replay detected")

    callback_status = data.get("status", "unknown")
    callback = AutomationCallback(
        id=generate_snowflake_id(),
        run_id=run.id,
        provider_execution_id=str(data.get("provider_execution_id", "")),
        status=callback_status,
        signature=signature,
        verified=True,
        payload_jsonb=data,
        received_at=datetime.now(timezone.utc),
    )
    db.add(callback)
    run.status = callback_status
    run.result_jsonb = data.get("result")
    if callback_status in _TERMINAL_AUTOMATION_STATUSES:
        run.finished_at = datetime.now(timezone.utc)
    if data.get("error"):
        run.error_summary = str(data.get("error"))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Callback replay detected") from exc
    return {"status": "accepted", "verified": True, "run_id": str(run.id)}


@router.get("/health", response_model=AutomationHealth)
async def check_automation_health() -> AutomationHealth:
    """Check health of the configured automation provider."""
    provider = automation_runtime_manager.get_provider()
    return await provider.health()


@router.get("/definitions", response_model=list[dict[str, Any]])
def list_automation_definitions(
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
) -> list[dict[str, Any]]:
    """List available automations in the system catalog."""
    defs = db.query(AutomationDefinition).filter(AutomationDefinition.enabled.is_(True)).all()
    return [
        {
            "id": str(d.id),
            "automation_key": d.automation_key,
            "name": d.name,
            "domain": d.domain,
            "provider": d.provider,
            "risk_level": d.risk_level,
            "approval_mode": d.approval_mode,
        }
        for d in defs
    ]


@router.post("/execute", response_model=AutomationRunResponse)
async def execute_automation(
    payload: ExecuteAutomationRequest,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
) -> AutomationRunResponse:
    """Execute an automation workflow through the active provider."""
    definition = (
        db.query(AutomationDefinition)
        .filter(AutomationDefinition.automation_key == payload.automation_key)
        .first()
    )
    if not definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown automation_key '{payload.automation_key}'",
        )

    if definition.approval_mode != "none":
        if payload.approval_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Automation '{payload.automation_key}' requires an approved approval_id",
            )

        approval = (
            db.query(AgentApproval)
            .filter(
                AgentApproval.id == payload.approval_id,
                AgentApproval.workspace_id == current_member.workspace_id,
            )
            .first()
        )
        if not approval:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Approval not found in this workspace")
        if approval.status != "approved":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Approval status is '{approval.status}', expected 'approved'",
            )
        if approval.tool_name != payload.automation_key:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Approval does not match this automation_key")

        already_used = (
            db.query(AutomationRun)
            .filter(AutomationRun.approval_id == payload.approval_id)
            .first()
        )
        if already_used:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Approval has already been consumed by another automation run",
            )

    run_id = generate_snowflake_id()
    now = datetime.now(timezone.utc)

    # 1. Create audit run record
    run = AutomationRun(
        id=run_id,
        workspace_id=current_member.workspace_id,
        company_id=current_member.workspace_id,
        automation_key=payload.automation_key,
        provider="mock" if os.getenv("COSA_AUTOMATION_PROVIDER", "mock") == "mock" else "n8n",
        agent_run_id=payload.agent_run_id,
        approval_id=payload.approval_id,
        status="running",
        risk_level=definition.risk_level,
        idempotency_key=payload.idempotency_key,
        payload_jsonb=payload.payload,
        started_at=now,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # 2. Dispatch to provider
    req = AutomationRequest(
        automation_key=payload.automation_key,
        execution_id=str(run_id),
        workspace_id=current_member.workspace_id,
        company_id=current_member.workspace_id,
        payload=payload.payload,
        idempotency_key=payload.idempotency_key,
    )

    provider = automation_runtime_manager.get_provider()
    start_res = await provider.execute(req)

    run.provider_execution_id = start_res.provider_execution_id
    if start_res.status in ("completed", "succeeded"):
        run.status = "succeeded"
        run.finished_at = datetime.now(timezone.utc)
    elif start_res.status == "failed":
        run.status = "failed"
        run.error_summary = start_res.error
        run.finished_at = datetime.now(timezone.utc)
    else:
        run.status = "running"

    db.commit()
    db.refresh(run)

    return AutomationRunResponse(
        id=str(run.id),
        workspace_id=str(run.workspace_id),
        automation_key=run.automation_key,
        provider=run.provider,
        provider_execution_id=run.provider_execution_id,
        status=run.status,
        started_at=run.started_at.isoformat(),
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
        result=run.result_jsonb,
        error_summary=run.error_summary,
    )


@router.post("/callback")
async def receive_automation_callback(
    request: Request,
    db: Session = Depends(get_db),
    x_cosa_signature: Optional[str] = Header(None, alias="X-COSA-Signature"),
    x_cosa_timestamp: Optional[str] = Header(None, alias="X-COSA-Timestamp"),
) -> dict[str, Any]:
    """Secure webhook endpoint receiving asynchronous execution callbacks from n8n."""
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")

    secret = os.getenv("N8N_WEBHOOK_SECRET", "cosa-n8n-default-secret")

    if not x_cosa_signature or not x_cosa_timestamp:
        raise HTTPException(status_code=401, detail="Missing callback signature")

    # Replay protection: reject callbacks whose timestamp has drifted too far from now,
    # so a captured signed payload cannot be resent indefinitely. X-COSA-Timestamp is the
    # same ISO8601 string format AutomationRequest.requested_at uses (see runtime/types.py).
    try:
        callback_time = datetime.fromisoformat(x_cosa_timestamp)
        if callback_time.tzinfo is None:
            callback_time = callback_time.replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid callback timestamp")
    if abs((datetime.now(timezone.utc) - callback_time).total_seconds()) > 300:
        raise HTTPException(status_code=401, detail="Callback timestamp outside allowed window")

    verified = verify_hmac_signature(secret, body_str, x_cosa_timestamp, x_cosa_signature)
    if not verified:
        raise HTTPException(status_code=401, detail="Callback signature verification failed")

    try:
        data = json.loads(body_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    return process_n8n_delegation_callback(
        db=db,
        data=data,
        signature=x_cosa_signature,
    )


@router.get("/runs/{run_id}", response_model=AutomationRunResponse)
def get_automation_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
) -> AutomationRunResponse:
    """Retrieve details and audit logs for a specific automation run."""
    run = (
        db.query(AutomationRun)
        .filter(AutomationRun.id == run_id, AutomationRun.workspace_id == current_member.workspace_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Automation run not found")

    return AutomationRunResponse(
        id=str(run.id),
        workspace_id=str(run.workspace_id),
        automation_key=run.automation_key,
        provider=run.provider,
        provider_execution_id=run.provider_execution_id,
        status=run.status,
        started_at=run.started_at.isoformat(),
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
        result=run.result_jsonb,
        error_summary=run.error_summary,
    )
