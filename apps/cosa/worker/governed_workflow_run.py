"""Task 11 (plan 2026-09-13-founder-configurable-agent-skill-workflow) — dispatch
`governed_workflow_run` scheduler tasks: build/load the execution manifest
exactly once, run it through `WorkflowOrchestration` (Tasks 8-10), and persist
enough durable state (`RunRecord`, checkpoint, run events) that a worker
restart resumes the exact same manifest/DAG state rather than re-resolving a
possibly-newer asset. Live re-authorization against Company deployment
authority happens INSIDE `AgentWorkflowStep.run()` (packages/agent/workflows/
agent_step.py) on every single step execution — including on resume, since
`resume_spec()` rebuilds fresh step instances and only re-runs steps not yet
completed — so a paused/revoked deployment fails closed mid-run without any
extra plumbing here.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from agent.contracts.run import RunStatus
from agent.runs.models import (
    GovernedWorkflowRunOutcome,
    RunCheckpointRecord,
    RunEventRecord,
    RunRecord,
)
from agent.workflows.manifest import (
    GovernedWorkflowRunManifest,
    ManifestConflictError,
    make_manifest,
)
from agent.workflows.models import Workflow, WorkflowStatus

logger = logging.getLogger("cosa.worker.governed_workflow_run")

__all__ = [
    "ManifestUnresolvableError",
    "execute_governed_workflow_run",
    "execute_governed_workflow_run_task",
    "resolve_or_create_manifest",
    "schedule_workflow_gate_resume",
]

_CHECKPOINT_STATE_KIND = "governed_workflow"

# Fields `make_manifest` cannot proceed without when building a manifest from
# scratch (as opposed to reloading a persisted one by run_id). A resume-only
# dispatch (e.g. `schedule_workflow_gate_resume`'s task, which carries only
# `run_id`/`workspace_id`) never has these — that's fine as long as a manifest
# already exists for the run_id; it's only an error if BOTH are missing.
_REQUIRED_NEW_MANIFEST_FIELDS = ("project_id", "workflow_asset_id", "workflow_definition_hash")


class ManifestUnresolvableError(Exception):
    """Raised when a `governed_workflow_run` dispatch has neither an existing
    durable manifest for its `run_id` nor enough payload fields to build one.
    Caught by `execute_governed_workflow_run_task` and turned into a safe,
    structured `failed` outcome — never left to propagate as a raw `KeyError`."""

    def __init__(self, run_id: str, reason_code: str) -> None:
        super().__init__(reason_code)
        self.run_id = run_id
        self.reason_code = reason_code


async def resolve_or_create_manifest(
    plane: Any, payload: dict[str, Any]
) -> GovernedWorkflowRunManifest:
    """Build the manifest exactly once per `run_id`, insert-once into the
    durable manifest repository. A later dispatch for the SAME run_id (worker
    restart, duplicate scheduler task from a retried Company event) always
    reloads the persisted manifest instead of resolving the workflow asset
    again — the whole point of pinning is that a founder publishing a newer
    workflow version mid-run must never change what's already executing.

    Raises `ManifestUnresolvableError` (never a raw `KeyError`) if no manifest
    exists yet for `run_id` and the payload doesn't carry enough to build one —
    e.g. a resume-only dispatch racing ahead of (or outliving) its manifest."""
    run_id = str(payload["run_id"])

    existing = await plane.run_repository.get_workflow_manifest(run_id)
    if existing is not None:
        return existing

    missing = [f for f in _REQUIRED_NEW_MANIFEST_FIELDS if not payload.get(f)]
    if missing:
        raise ManifestUnresolvableError(run_id, "governed_workflow_manifest_unresolvable")

    manifest = make_manifest(
        run_id=run_id,
        project_id=str(payload["project_id"]),
        workspace_id=str(payload["workspace_id"]),
        workflow_asset_id=str(payload["workflow_asset_id"]),
        workflow_version=str(payload.get("workflow_version", "1.0.0")),
        workflow_definition_hash=payload.get("workflow_definition_hash"),
        role_deployment_id=payload.get("role_deployment_id"),
        project_agent_deployment_id=payload.get("project_agent_deployment_id"),
        pinned_agent_specs=payload.get("pinned_agent_specs") or {},
        pinned_skill_specs=payload.get("pinned_skill_specs") or {},
        capability_allowlist=payload.get("capability_allowlist") or [],
        budget_limit=payload.get("budget_limit") or {},
        trigger_id=payload.get("workflow_binding_id"),
        correlation_id=payload.get("correlation_id"),
    )
    try:
        return await plane.run_repository.create_workflow_manifest(manifest)
    except ManifestConflictError:
        # Race: another worker (or an earlier attempt in this same process,
        # e.g. a duplicate scheduler task) inserted it first — reload rather
        # than trust the copy we just built.
        loaded = await plane.run_repository.get_workflow_manifest(run_id)
        if loaded is None:  # pragma: no cover - defensive, repository invariant
            raise
        return loaded


def _sanitize_state(state: dict[str, Any]) -> dict[str, Any]:
    """Strip internal bookkeeping keys (notably `_manifest`, a live Pydantic
    object) before persisting workflow state to a checkpoint/`final_output` —
    those columns must stay plain JSON, and the manifest is always re-supplied
    explicitly by the caller on resume rather than reconstructed from a
    snapshot (never trust a serialized copy of a pinned dependency)."""
    return {k: v for k, v in state.items() if k != "_manifest"}


async def execute_governed_workflow_run(
    plane: Any,
    manifest: GovernedWorkflowRunManifest,
    *,
    stream_mgr: Any | None = None,
) -> GovernedWorkflowRunOutcome:
    """Execute (or resume) one governed workflow run for an already-built
    manifest. Safe to call repeatedly with the same manifest — a run already
    COMPLETED/FAILED is a terminal no-op reload of its outcome; a run
    WAITING_APPROVAL resumes from its last durable checkpoint."""
    run_id = manifest.run_id
    workspace_id = manifest.workspace_id
    project_id = manifest.project_id
    conversation_id = f"wf:{run_id}"

    async def _emit(event_type: str, body: dict[str, Any]) -> None:
        await plane.run_repository.append_event(
            RunEventRecord(
                run_id=run_id,
                project_id=project_id,
                event_type=event_type,
                payload=body,
                correlation_id=manifest.correlation_id,
            )
        )
        if stream_mgr is None:
            return
        repo = getattr(plane, "stream_event_repository", None)
        if repo is None:
            return
        with contextlib.suppress(Exception):
            await stream_mgr.emit(
                repo,
                run_id=run_id,
                conversation_id=conversation_id,
                event_type=event_type,
                payload=body,
                correlation_id=manifest.correlation_id,
                activity_service=getattr(plane, "project_activity_service", None),
                workspace_id=workspace_id,
                project_id=project_id,
            )

    run = await plane.run_repository.get_run(run_id)
    resuming = run is not None and run.status == RunStatus.WAITING_APPROVAL

    if run is None:
        run = await plane.run_repository.create_run(
            RunRecord(
                run_id=run_id,
                workspace_id=workspace_id,
                project_id=project_id,
                principal=f"system:governed_workflow:{workspace_id}",
                root_executable_id=manifest.workflow_asset_id,
                root_executable_kind="workflow",
                root_executable_version=manifest.workflow_version,
                root_definition_hash=manifest.workflow_definition_hash,
                correlation_id=manifest.correlation_id,
                idempotency_key=manifest.trigger_id,
                status=RunStatus.RUNNING,
            )
        )
        await _emit(
            "run.started",
            {
                "workflow_asset_id": manifest.workflow_asset_id,
                "manifest_hash": manifest.manifest_hash,
            },
        )
    elif run.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
        # Terminal run replayed (duplicate task) — report the exact stored
        # outcome instead of re-executing side effects a second time.
        return GovernedWorkflowRunOutcome(
            run_id=run_id,
            status=run.status.value,
            error=run.error_details.get("reason") if run.error_details else None,
        )
    else:
        await plane.run_repository.update_run_status(run_id, RunStatus.RUNNING)

    orchestration = plane.workflow_orchestration
    try:
        if resuming:
            checkpoint = await plane.run_repository.get_latest_checkpoint(run_id)
            if checkpoint is None or checkpoint.state_kind != _CHECKPOINT_STATE_KIND:
                raise RuntimeError(
                    f"run {run_id} is WAITING_APPROVAL but has no durable governed workflow checkpoint to resume from"
                )
            workflow = Workflow.model_validate(checkpoint.serialized_state["workflow"])
            workflow_result = await orchestration.resume_manifest(manifest, workflow)
        else:
            workflow_result = await orchestration.execute_manifest(manifest)
    except Exception:
        logger.exception("governed workflow run failed", extra={"run_id": run_id})
        await plane.run_repository.update_run_status(
            run_id, RunStatus.FAILED, error_details={"reason": "governed_workflow_execution_error"}
        )
        await _emit("run.failed", {"error": "governed_workflow_execution_error"})
        return GovernedWorkflowRunOutcome(
            run_id=run_id, status="failed", error="governed_workflow_execution_error"
        )

    # Persist the DAG state as a durable checkpoint regardless of outcome —
    # a run left WAITING_APPROVAL (or one that crashes right after this point)
    # must reload the exact same in-flight Workflow object on the next attempt,
    # not start the whole manifest over.
    existing_checkpoints = await plane.run_repository.list_checkpoints(run_id)
    # Sanitize BEFORE dumping — `workflow_result.state["_manifest"]` is a live
    # Pydantic object; drop it first so this checkpoint stays plain JSON.
    sanitized_for_checkpoint = workflow_result.model_copy(
        update={"state": _sanitize_state(workflow_result.state)}
    )
    await plane.run_repository.save_checkpoint(
        RunCheckpointRecord(
            run_id=run_id,
            project_id=project_id,
            sequence_no=len(existing_checkpoints) + 1,
            step_name=workflow_result.failed_step_name or "governed_workflow",
            state_kind=_CHECKPOINT_STATE_KIND,
            serialized_state={"workflow": sanitized_for_checkpoint.model_dump(mode="json")},
            manifest_snapshot=manifest.manifest_json,
        )
    )

    if workflow_result.status == WorkflowStatus.COMPLETED:
        await plane.run_repository.update_run_status(
            run_id, RunStatus.COMPLETED, final_output=_sanitize_state(workflow_result.state)
        )
        await _emit("run.completed", {"run_id": run_id})
        return GovernedWorkflowRunOutcome(run_id=run_id, status="completed")

    if workflow_result.status == WorkflowStatus.WAITING_APPROVAL:
        await plane.run_repository.update_run_status(run_id, RunStatus.WAITING_APPROVAL)
        await _emit(
            "run.waiting_approval", {"pending_approval_id": workflow_result.pending_approval_id}
        )
        return GovernedWorkflowRunOutcome(
            run_id=run_id,
            status="waiting_approval",
            pending_approval_id=workflow_result.pending_approval_id,
        )

    safe_reason = workflow_result.error or "governed_workflow_step_failed"
    await plane.run_repository.update_run_status(
        run_id,
        RunStatus.FAILED,
        error_details={"failed_step": workflow_result.failed_step_name, "reason": safe_reason},
    )
    await _emit(
        "run.failed", {"failed_step": workflow_result.failed_step_name, "reason": safe_reason}
    )
    return GovernedWorkflowRunOutcome(run_id=run_id, status="failed", error=safe_reason)


async def execute_governed_workflow_run_task(
    plane: Any,
    stream_mgr: Any,
    payload: dict[str, Any],
) -> GovernedWorkflowRunOutcome:
    """Worker task-level entrypoint for `task_type == "governed_workflow_run"`
    — builds/loads the manifest from the scheduler payload, then executes it."""
    try:
        manifest = await resolve_or_create_manifest(plane, payload)
    except ManifestUnresolvableError as exc:
        logger.error(
            "governed workflow run has no resolvable manifest",
            extra={"run_id": exc.run_id, "reason_code": exc.reason_code},
        )
        return GovernedWorkflowRunOutcome(run_id=exc.run_id, status="failed", error=exc.reason_code)
    return await execute_governed_workflow_run(plane, manifest, stream_mgr=stream_mgr)


async def schedule_workflow_gate_resume(
    plane: Any,
    payload: dict[str, Any],
) -> tuple[bool, str | None]:
    """Approval-action handler for `subject_kind == "workflow_gate"` (Task 11).

    An `ApprovalGateStep` approval (`packages/agent/workflows/approval_step.py`)
    carries the exact `run_id` of the governed workflow it paused in
    `RunApprovalRecord.requirement["run_id"]` — a plain JSONB column, chosen
    specifically because `chk_agent_approvals_binding` (packages/agent/
    migrations/006_unified_governance_approvals.sql) forbids storing it on
    the `run_id` column itself for a CHANGE_REQUEST binding, and because
    string-splitting it out of `subject_ref` (an earlier version of this
    function did) is unsafe: `workspace_id`/`idempotency_key` — which
    together form the governed run's `run_id`, see
    `apps/cosa/events/router.py` — are not charset-validated and could
    legally contain the delimiter, silently truncating the parsed id.

    This re-loads the approval by id (never trusts the outbox-relayed
    payload alone) and schedules a fresh `governed_workflow_run` task for
    that run_id, coalesced the same way the router's initial trigger is — so
    an approved gate actually reaches `execute_governed_workflow_run`'s
    resume path in production, not only when a test calls it a second time
    by hand. Returns `(success, reason_code_if_not)` — never raises for a
    malformed/legacy approval record, so a bad or missing run_id fails
    closed with a safe reason code instead of an unhandled exception.
    """
    approval_id = payload.get("approval_id")
    workspace_id = payload.get("workspace_id")
    if not approval_id or not workspace_id:
        return False, "INVALID_PAYLOAD"

    approval = await plane.run_repository.get_scoped_approval(approval_id, workspace_id)
    if approval is None:
        return False, "APPROVAL_NOT_FOUND"
    if approval.status != "approved":
        return False, "APPROVAL_NOT_APPROVED"

    run_id = (approval.requirement or {}).get("run_id")
    if not run_id or not isinstance(run_id, str):
        return False, "APPROVAL_MISSING_RUN_ID"

    await plane.scheduler.schedule(
        target_spec_id=run_id,
        target_spec_kind="agent",
        input_payload={
            "task_type": "governed_workflow_run",
            "run_id": run_id,
            "workspace_id": workspace_id,
        },
        coalescing_key=f"governed_workflow_run:{workspace_id}:{run_id}",
    )
    return True, None
