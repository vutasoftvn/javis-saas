from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.agents.execution.artifacts import collect_and_store_artifacts
from app.agents.execution.credential_broker import CredentialBroker
from app.agents.execution.errors import ExecutionErrorCode, ExecutionRuntimeError
from app.agents.execution.manager import execution_provider_manager
from app.agents.execution.models import ExecutionJob, ExecutionStep
from app.agents.execution.n8n_bridge import dispatch_job_callback
from app.agents.execution.policies import load_policy
from app.agents.execution.redaction import redact
from app.agents.execution.types import ExecutionJobResult, ExecutionStatus, SandboxPolicy
from app.agents.capabilities.service import CapabilityGateway
from app.agents.governance.approval_service import ApprovalService
from app.agents.governance.models import AgentEventRecord
from app.agents.governance.policy_engine import (
    PermissionLevel,
    PolicyAction,
    PolicyEngine,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def run_execution_job(db: Session, job_id: int) -> ExecutionJobResult:
    """Execute a single queued execution job from end to end."""
    job = db.query(ExecutionJob).filter(ExecutionJob.id == job_id).first()
    if not job:
        raise ExecutionRuntimeError(
            code=ExecutionErrorCode.EXEC_JOB_NOT_FOUND,
            message=f"Execution job {job_id} not found",
        )

    meta = job.metadata_jsonb or {}
    policy_name = meta.get("policy_name", "safe_analysis")
    policy: SandboxPolicy = load_policy(db, job.workspace_id, policy_name)

    # 1. Policy Gate Evaluation via CapabilityGateway
    check_result = await CapabilityGateway.check(
        db=db,
        workspace_id=job.workspace_id,
        subject_type="agent",
        subject_id=job.agent_key,
        capability="code.execute",
        resource_type="sandbox",
        permission_profile="l3_execute",
        params=meta,
    )

    if check_result.action == PolicyAction.DENY.value:
        job.status = ExecutionStatus.BLOCKED.value
        job.error_code = ExecutionErrorCode.EXEC_POLICY_VIOLATION.value
        job.error_message = redact(check_result.reason or "Execution blocked by policy engine")
        job.completed_at = utc_now()
        db.commit()
        return _build_result(job, [])

    if check_result.action == PolicyAction.REQUIRE_APPROVAL.value:
        approval = ApprovalService.get_pending_approval_for_run(db, job.agent_run_id) if job.agent_run_id else None
        if not approval or approval.status != "approved":
            job.status = ExecutionStatus.AWAITING_APPROVAL.value
            db.commit()
            return _build_result(job, [])

    # 2. Preparing phase
    job.status = ExecutionStatus.PREPARING.value
    job.started_at = utc_now()
    db.commit()

    provider = execution_provider_manager.get(job.provider)
    sandbox_id = None
    step_results = []
    artifacts = []

    try:
        # 2.5 Resolve Allowed Credentials via CredentialBroker
        sandbox_env = CredentialBroker.resolve_credentials(
            db=db,
            workspace_id=job.workspace_id,
            policy=policy,
            requested_services=meta.get("requested_credentials"),
        )

        # 3. Create Ephemeral Sandbox
        sandbox_id = await provider.create_workspace(
            policy=policy,
            metadata={"job_id": job.id, "workspace_id": job.workspace_id, "agent_key": job.agent_key},
            env=sandbox_env,
        )
        job.sandbox_id = sandbox_id
        db.commit()

        # 4. Upload Input Files
        input_files: Dict[str, Any] = meta.get("input_files", {})
        for rel_path, file_data in input_files.items():
            raw_bytes = file_data.encode("utf-8") if isinstance(file_data, str) else file_data
            target_path = f"/input/{rel_path.lstrip('/')}"
            await provider.upload_file(sandbox_id, target_path, raw_bytes)

        # 5. Running phase: Execute Commands
        job.status = ExecutionStatus.RUNNING.value
        db.commit()

        commands: List[str] = meta.get("commands", [])
        has_failed = False

        for seq, cmd in enumerate(commands, start=1):
            step_record = ExecutionStep(
                job_id=job.id,
                sequence=seq,
                step_type="command",
                command=cmd,
                status="running",
                started_at=utc_now(),
            )
            db.add(step_record)
            db.commit()

            step_res = await provider.execute(
                sandbox_id=sandbox_id,
                command=cmd,
                timeout_seconds=policy.timeout_seconds,
            )

            # Redact logs before persisting to DB
            step_record.status = step_res.status
            step_record.exit_code = step_res.exit_code
            step_record.stdout_excerpt = redact(step_res.stdout_excerpt)
            step_record.stderr_excerpt = redact(step_res.stderr_excerpt)
            step_record.completed_at = utc_now()
            db.commit()

            step_results.append(step_res)

            if step_res.exit_code != 0 or step_res.status != "completed":
                has_failed = True
                job.error_code = ExecutionErrorCode.EXEC_COMMAND_FAILED.value
                job.error_message = redact(f"Command failed with exit code {step_res.exit_code}: {step_res.stderr_excerpt}")
                break

        # 6. Collecting phase: Collect Artifacts
        job.status = ExecutionStatus.COLLECTING.value
        db.commit()

        artifacts = await collect_and_store_artifacts(
            db=db,
            workspace_id=job.workspace_id,
            user_id=job.user_id,
            job_id=job.id,
            sandbox_id=sandbox_id,
            provider=provider,
            policy=policy,
        )

        job.status = ExecutionStatus.FAILED.value if has_failed else ExecutionStatus.COMPLETED.value
        job.completed_at = utc_now()

    except Exception as exc:
        logger.exception(f"[run_execution_job] Error running job {job.id}: {exc}")
        job.status = ExecutionStatus.FAILED.value
        job.error_code = getattr(exc, "code", ExecutionErrorCode.EXEC_INTERNAL_ERROR).value if hasattr(getattr(exc, "code", None), "value") else str(getattr(exc, "code", ExecutionErrorCode.EXEC_INTERNAL_ERROR))
        job.error_message = redact(str(exc))
        job.completed_at = utc_now()

    finally:
        # 7. Always Terminate & Destroy Sandbox (ephemeral guarantee)
        if sandbox_id:
            try:
                await provider.terminate(sandbox_id)
                job.destroyed_at = utc_now()
            except Exception as term_exc:
                logger.warning(f"[run_execution_job] Could not terminate sandbox {sandbox_id}: {term_exc}")

        # 8. Record audit event in agent_events
        if job.agent_run_id:
            try:
                audit_event = AgentEventRecord(
                    run_id=job.agent_run_id,
                    sequence=1,
                    agent_key=job.agent_key,
                    event_type="execution_job_completed" if job.status == ExecutionStatus.COMPLETED.value else "execution_job_failed",
                    status=job.status,
                    actor_type="execution_job",
                    actor_id=str(job.id),
                    payload_jsonb={
                        "job_id": str(job.id),
                        "status": job.status,
                        "provider": job.provider,
                        "artifact_count": len(artifacts),
                        "error_code": job.error_code,
                    },
                )
                db.add(audit_event)

                CapabilityGateway.record_observation(
                    db=db,
                    run_id=job.agent_run_id,
                    agent_key=job.agent_key,
                    tool_name="code.execute",
                    status="success" if job.status == ExecutionStatus.COMPLETED.value else "failed",
                    capability="code.execute",
                    resource_type="sandbox",
                    resource_id=job.sandbox_id,
                    input_data=meta,
                    output_data={"job_id": str(job.id), "artifact_count": len(artifacts), "status": job.status},
                )
            except Exception as audit_exc:
                logger.warning(f"[run_execution_job] Failed to record audit event: {audit_exc}")

        db.commit()

    result = _build_result(job, step_results, artifacts)

    # 9. Optional Async Webhook Callback (n8n integration)
    callback_url = meta.get("callback_url")
    if callback_url:
        webhook_secret = meta.get("webhook_secret") or "cosa-n8n-default-secret"
        try:
            await dispatch_job_callback(callback_url, webhook_secret, result)
        except Exception as cb_exc:
            logger.warning(f"[run_execution_job] Failed to dispatch callback to {callback_url}: {cb_exc}")

    return result


def _build_result(job: ExecutionJob, steps: list, artifacts: list = None) -> ExecutionJobResult:
    return ExecutionJobResult(
        job_id=str(job.id),
        workspace_id=job.workspace_id,
        status=ExecutionStatus(job.status),
        provider=job.provider,
        sandbox_id=job.sandbox_id,
        steps=steps,
        artifacts=artifacts or [],
        error_code=job.error_code,
        error_message=job.error_message,
        created_at=job.created_at or utc_now(),
        started_at=job.started_at,
        completed_at=job.completed_at,
        destroyed_at=job.destroyed_at,
    )
