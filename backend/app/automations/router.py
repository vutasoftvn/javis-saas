from datetime import datetime, timezone
import json
import os
from typing import Any, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.automations.models import AutomationCallback, AutomationDefinition, AutomationRun
from app.automations.runtime.adapters.n8n import verify_hmac_signature
from app.automations.runtime.manager import automation_runtime_manager
from app.automations.runtime.types import AutomationHealth, AutomationRequest
from app.core.auth import get_current_workspace_member
from app.core.snowflake import generate_snowflake_id, generate_snowflake_str
from app.db.models import WorkspaceMember
from app.db.session import get_db

router = APIRouter()


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
    if not defs:
        # Fallback default catalog definitions if DB is freshly created
        return [
            {
                "automation_key": "system.telegram_notification",
                "name": "Telegram Notification",
                "domain": "system",
                "provider": "n8n",
                "risk_level": "low",
                "approval_mode": "none",
            },
            {
                "automation_key": "sales.followup_email",
                "name": "Sales Follow-up Email",
                "domain": "sales",
                "provider": "n8n",
                "risk_level": "medium",
                "approval_mode": "policy_based",
            },
        ]
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
        risk_level="low",
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
    verified = False

    if x_cosa_signature and x_cosa_timestamp:
        verified = verify_hmac_signature(secret, body_str, x_cosa_timestamp, x_cosa_signature)

    try:
        data = json.loads(body_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    exec_id = data.get("execution_id")
    if not exec_id:
        raise HTTPException(status_code=400, detail="Missing execution_id in callback")

    try:
        run_id_int = int(exec_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid execution_id format")

    run = db.query(AutomationRun).filter(AutomationRun.id == run_id_int).first()
    if not run:
        raise HTTPException(status_code=404, detail="AutomationRun not found")

    # Record callback audit
    callback = AutomationCallback(
        id=generate_snowflake_id(),
        run_id=run.id,
        provider_execution_id=str(data.get("provider_execution_id", "")),
        status=data.get("status", "unknown"),
        signature=x_cosa_signature or "none",
        verified=verified,
        payload_jsonb=data,
        received_at=datetime.now(timezone.utc),
    )
    db.add(callback)

    # Update run status
    run.status = data.get("status", run.status)
    run.result_jsonb = data.get("result")
    run.finished_at = datetime.now(timezone.utc)
    if data.get("error"):
        run.error_summary = str(data.get("error"))

    db.commit()

    return {"status": "accepted", "verified": verified, "run_id": str(run.id)}


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
