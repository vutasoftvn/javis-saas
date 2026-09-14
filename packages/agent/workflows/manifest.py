from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

__all__ = [
    "GovernedWorkflowRunManifest",
    "InMemoryWorkflowManifestRepository",
    "ManifestConflictError",
    "PostgresWorkflowManifestRepository",
    "StepRecordConflictError",
    "WorkflowManifestRepository",
    "WorkflowStepRecord",
    "make_manifest",
]


class ManifestConflictError(Exception):
    """Raised when an attempt is made to insert a duplicate execution manifest for a run."""

    pass


class StepRecordConflictError(Exception):
    """Raised when an attempt is made to insert a duplicate step record for a run."""

    pass


class GovernedWorkflowRunManifest(BaseModel):
    """Execution manifest pinning workflow definition, policies, deployments and runtime bounds."""

    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:16]}")
    manifest_hash: str | None = None
    project_id: str
    workspace_id: str = "default"
    workflow_asset_id: str
    workflow_version: str = "1.0.0"
    workflow_definition_hash: str
    role_deployment_id: str | None = None
    project_agent_deployment_id: str | None = None
    pinned_agent_specs: dict[str, Any] = Field(default_factory=dict)
    pinned_skill_specs: dict[str, Any] = Field(default_factory=dict)
    policy_epoch: str = "v1"
    policy_hash: str = Field(default_factory=lambda: hashlib.sha256(b"default_policy").hexdigest())
    capability_allowlist: list[str] = Field(default_factory=list)
    budget_limit: dict[str, Any] = Field(default_factory=dict)
    trigger_id: str | None = None
    correlation_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    manifest_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def compute_hash(self) -> str:
        payload = {
            "project_id": self.project_id,
            "workspace_id": self.workspace_id,
            "workflow_asset_id": self.workflow_asset_id,
            "workflow_version": self.workflow_version,
            "workflow_definition_hash": self.workflow_definition_hash,
            "role_deployment_id": self.role_deployment_id,
            "project_agent_deployment_id": self.project_agent_deployment_id,
            "pinned_agent_specs": self.pinned_agent_specs,
            "pinned_skill_specs": self.pinned_skill_specs,
            "policy_epoch": self.policy_epoch,
            "policy_hash": self.policy_hash,
            "capability_allowlist": sorted(self.capability_allowlist),
            "budget_limit": self.budget_limit,
        }
        canonical_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def model_post_init(self, __context: Any) -> None:
        if not self.manifest_hash:
            self.manifest_hash = self.compute_hash()
        if not self.manifest_json:
            self.manifest_json = self.model_dump(mode="json", exclude={"manifest_json"})


class WorkflowStepRecord(BaseModel):
    """Durable ledger record for workflow step execution state without raw prompt or secrets."""

    step_record_id: str = Field(default_factory=lambda: f"steprec_{uuid.uuid4().hex[:16]}")
    run_id: str
    step_id: str
    step_name: str
    sequence_no: int
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, WAITING_APPROVAL
    checkpoint_ref: str | None = None
    input_hash: str
    output_hash: str | None = None
    safe_reason_code: str | None = None
    error_details: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


def make_manifest(
    *,
    run_id: str | None = None,
    project_id: str = "proj-default",
    workspace_id: str = "default",
    workflow_asset_id: str = "wf_default",
    workflow_version: str = "1.0.0",
    workflow_definition_hash: str | None = None,
    role_deployment_id: str | None = None,
    project_agent_deployment_id: str | None = None,
    pinned_agent_specs: dict[str, Any] | None = None,
    pinned_skill_specs: dict[str, Any] | None = None,
    policy_epoch: str = "v1",
    policy_hash: str | None = None,
    capability_allowlist: list[str] | None = None,
    budget_limit: dict[str, Any] | None = None,
    trigger_id: str | None = None,
    correlation_id: str | None = None,
    evidence_refs: list[str] | None = None,
) -> GovernedWorkflowRunManifest:
    rid = run_id or f"run_{uuid.uuid4().hex[:16]}"
    def_hash = (
        workflow_definition_hash
        or hashlib.sha256(f"wf_{workflow_asset_id}:{workflow_version}".encode()).hexdigest()
    )
    pol_hash = policy_hash or hashlib.sha256(b"default_policy_epoch_v1").hexdigest()

    manifest = GovernedWorkflowRunManifest(
        run_id=rid,
        project_id=project_id,
        workspace_id=workspace_id,
        workflow_asset_id=workflow_asset_id,
        workflow_version=workflow_version,
        workflow_definition_hash=def_hash,
        role_deployment_id=role_deployment_id,
        project_agent_deployment_id=project_agent_deployment_id,
        pinned_agent_specs=pinned_agent_specs or {},
        pinned_skill_specs=pinned_skill_specs or {},
        policy_epoch=policy_epoch,
        policy_hash=pol_hash,
        capability_allowlist=capability_allowlist or [],
        budget_limit=budget_limit or {},
        trigger_id=trigger_id,
        correlation_id=correlation_id,
        evidence_refs=evidence_refs or [],
    )
    return manifest


class WorkflowManifestRepository(Protocol):
    async def create_manifest(
        self, manifest: GovernedWorkflowRunManifest
    ) -> GovernedWorkflowRunManifest: ...
    async def get_manifest(self, run_id: str) -> GovernedWorkflowRunManifest | None: ...
    async def get_manifest_by_hash(
        self, manifest_hash: str
    ) -> GovernedWorkflowRunManifest | None: ...
    async def create_step_record(self, record: WorkflowStepRecord) -> WorkflowStepRecord: ...
    async def update_step_record(self, record: WorkflowStepRecord) -> WorkflowStepRecord: ...
    async def get_step_records(self, run_id: str) -> list[WorkflowStepRecord]: ...


class InMemoryWorkflowManifestRepository:
    def __init__(self) -> None:
        self._manifests: dict[str, GovernedWorkflowRunManifest] = {}
        self._by_hash: dict[str, GovernedWorkflowRunManifest] = {}
        self._step_records: dict[
            tuple[str, str], WorkflowStepRecord
        ] = {}  # (run_id, step_id) -> record

    async def create_manifest(
        self, manifest: GovernedWorkflowRunManifest
    ) -> GovernedWorkflowRunManifest:
        if manifest.run_id in self._manifests:
            raise ManifestConflictError(f"Manifest for run {manifest.run_id} already exists")
        if not manifest.manifest_hash:
            manifest.manifest_hash = manifest.compute_hash()
        self._manifests[manifest.run_id] = manifest
        self._by_hash[manifest.manifest_hash] = manifest
        return manifest

    async def get_manifest(self, run_id: str) -> GovernedWorkflowRunManifest | None:
        return self._manifests.get(run_id)

    async def get_manifest_by_hash(self, manifest_hash: str) -> GovernedWorkflowRunManifest | None:
        return self._by_hash.get(manifest_hash)

    async def create_step_record(self, record: WorkflowStepRecord) -> WorkflowStepRecord:
        key = (record.run_id, record.step_id)
        if key in self._step_records:
            raise StepRecordConflictError(f"Step record for {key} already exists")
        self._step_records[key] = record
        return record

    async def update_step_record(self, record: WorkflowStepRecord) -> WorkflowStepRecord:
        key = (record.run_id, record.step_id)
        self._step_records[key] = record
        return record

    async def get_step_records(self, run_id: str) -> list[WorkflowStepRecord]:
        return sorted(
            [r for (rid, _), r in self._step_records.items() if rid == run_id],
            key=lambda r: r.sequence_no,
        )


class PostgresWorkflowManifestRepository(WorkflowManifestRepository):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | Callable[[], AsyncSession] | Any,
    ) -> None:
        self._session_factory = session_factory

    async def create_manifest(
        self, manifest: GovernedWorkflowRunManifest
    ) -> GovernedWorkflowRunManifest:
        if not manifest.manifest_hash:
            manifest.manifest_hash = manifest.compute_hash()

        stmt = text(
            """
            INSERT INTO agent.workflow_execution_manifests (
                run_id, manifest_hash, project_id, workspace_id, workflow_asset_id, workflow_version,
                workflow_definition_hash, role_deployment_id, project_agent_deployment_id,
                pinned_agent_specs, pinned_skill_specs, policy_epoch, policy_hash,
                capability_allowlist, budget_limit, trigger_id, correlation_id, evidence_refs,
                manifest_json, created_at
            )
            VALUES (
                :run_id, :manifest_hash, :project_id, :workspace_id, :workflow_asset_id, :workflow_version,
                :workflow_definition_hash, :role_deployment_id, :project_agent_deployment_id,
                CAST(:pinned_agent_specs AS jsonb), CAST(:pinned_skill_specs AS jsonb),
                :policy_epoch, :policy_hash, CAST(:capability_allowlist AS jsonb),
                CAST(:budget_limit AS jsonb), :trigger_id, :correlation_id,
                CAST(:evidence_refs AS jsonb), CAST(:manifest_json AS jsonb), :created_at
            )
            ON CONFLICT (run_id) DO NOTHING
            RETURNING run_id
            """
        )
        async with self._session_factory() as session, session.begin():
            res = await session.execute(
                stmt,
                {
                    "run_id": manifest.run_id,
                    "manifest_hash": manifest.manifest_hash,
                    "project_id": manifest.project_id,
                    "workspace_id": manifest.workspace_id,
                    "workflow_asset_id": manifest.workflow_asset_id,
                    "workflow_version": manifest.workflow_version,
                    "workflow_definition_hash": manifest.workflow_definition_hash,
                    "role_deployment_id": manifest.role_deployment_id,
                    "project_agent_deployment_id": manifest.project_agent_deployment_id,
                    "pinned_agent_specs": json.dumps(manifest.pinned_agent_specs),
                    "pinned_skill_specs": json.dumps(manifest.pinned_skill_specs),
                    "policy_epoch": manifest.policy_epoch,
                    "policy_hash": manifest.policy_hash,
                    "capability_allowlist": json.dumps(manifest.capability_allowlist),
                    "budget_limit": json.dumps(manifest.budget_limit),
                    "trigger_id": manifest.trigger_id,
                    "correlation_id": manifest.correlation_id,
                    "evidence_refs": json.dumps(manifest.evidence_refs),
                    "manifest_json": json.dumps(
                        manifest.manifest_json or manifest.model_dump(mode="json")
                    ),
                    "created_at": manifest.created_at,
                },
            )
            row = res.mappings().one_or_none()
            if not row:
                raise ManifestConflictError(f"Manifest for run '{manifest.run_id}' already exists")
            return manifest

    async def get_manifest(self, run_id: str) -> GovernedWorkflowRunManifest | None:
        stmt = text(
            """
            SELECT run_id, manifest_hash, project_id, workspace_id, workflow_asset_id, workflow_version,
                   workflow_definition_hash, role_deployment_id, project_agent_deployment_id,
                   pinned_agent_specs, pinned_skill_specs, policy_epoch, policy_hash,
                   capability_allowlist, budget_limit, trigger_id, correlation_id, evidence_refs,
                   manifest_json, created_at
            FROM agent.workflow_execution_manifests
            WHERE run_id = :run_id
            LIMIT 1
            """
        )
        async with self._session_factory() as session:
            res = await session.execute(stmt, {"run_id": run_id})
            row = res.mappings().one_or_none()
            if not row:
                return None
            return self._row_to_manifest(row)

    async def get_manifest_by_hash(self, manifest_hash: str) -> GovernedWorkflowRunManifest | None:
        stmt = text(
            """
            SELECT run_id, manifest_hash, project_id, workspace_id, workflow_asset_id, workflow_version,
                   workflow_definition_hash, role_deployment_id, project_agent_deployment_id,
                   pinned_agent_specs, pinned_skill_specs, policy_epoch, policy_hash,
                   capability_allowlist, budget_limit, trigger_id, correlation_id, evidence_refs,
                   manifest_json, created_at
            FROM agent.workflow_execution_manifests
            WHERE manifest_hash = :manifest_hash
            LIMIT 1
            """
        )
        async with self._session_factory() as session:
            res = await session.execute(stmt, {"manifest_hash": manifest_hash})
            row = res.mappings().one_or_none()
            if not row:
                return None
            return self._row_to_manifest(row)

    async def create_step_record(self, record: WorkflowStepRecord) -> WorkflowStepRecord:
        stmt = text(
            """
            INSERT INTO agent.workflow_step_records (
                step_record_id, run_id, step_id, step_name, sequence_no, status, checkpoint_ref,
                input_hash, output_hash, safe_reason_code, error_details, created_at, completed_at
            )
            VALUES (
                :step_record_id, :run_id, :step_id, :step_name, :sequence_no, :status, :checkpoint_ref,
                :input_hash, :output_hash, :safe_reason_code, CAST(:error_details AS jsonb),
                :created_at, :completed_at
            )
            ON CONFLICT (run_id, step_id) DO NOTHING
            RETURNING step_record_id
            """
        )
        async with self._session_factory() as session, session.begin():
            res = await session.execute(
                stmt,
                {
                    "step_record_id": record.step_record_id,
                    "run_id": record.run_id,
                    "step_id": record.step_id,
                    "step_name": record.step_name,
                    "sequence_no": record.sequence_no,
                    "status": record.status,
                    "checkpoint_ref": record.checkpoint_ref,
                    "input_hash": record.input_hash,
                    "output_hash": record.output_hash,
                    "safe_reason_code": record.safe_reason_code,
                    "error_details": json.dumps(record.error_details)
                    if record.error_details
                    else None,
                    "created_at": record.created_at,
                    "completed_at": record.completed_at,
                },
            )
            row = res.mappings().one_or_none()
            if not row:
                raise StepRecordConflictError(
                    f"Step record for run '{record.run_id}' step '{record.step_id}' already exists"
                )
            return record

    async def update_step_record(self, record: WorkflowStepRecord) -> WorkflowStepRecord:
        stmt = text(
            """
            UPDATE agent.workflow_step_records
            SET status = :status,
                checkpoint_ref = :checkpoint_ref,
                output_hash = :output_hash,
                safe_reason_code = :safe_reason_code,
                error_details = CAST(:error_details AS jsonb),
                completed_at = :completed_at
            WHERE run_id = :run_id AND step_id = :step_id
            RETURNING step_record_id
            """
        )
        async with self._session_factory() as session, session.begin():
            await session.execute(
                stmt,
                {
                    "run_id": record.run_id,
                    "step_id": record.step_id,
                    "status": record.status,
                    "checkpoint_ref": record.checkpoint_ref,
                    "output_hash": record.output_hash,
                    "safe_reason_code": record.safe_reason_code,
                    "error_details": json.dumps(record.error_details)
                    if record.error_details
                    else None,
                    "completed_at": record.completed_at,
                },
            )
            return record

    async def get_step_records(self, run_id: str) -> list[WorkflowStepRecord]:
        stmt = text(
            """
            SELECT step_record_id, run_id, step_id, step_name, sequence_no, status, checkpoint_ref,
                   input_hash, output_hash, safe_reason_code, error_details, created_at, completed_at
            FROM agent.workflow_step_records
            WHERE run_id = :run_id
            ORDER BY sequence_no ASC
            """
        )
        async with self._session_factory() as session:
            res = await session.execute(stmt, {"run_id": run_id})
            rows = res.mappings().all()
            return [
                WorkflowStepRecord(
                    step_record_id=r["step_record_id"],
                    run_id=r["run_id"],
                    step_id=r["step_id"],
                    step_name=r["step_name"],
                    sequence_no=r["sequence_no"],
                    status=r["status"],
                    checkpoint_ref=r["checkpoint_ref"],
                    input_hash=r["input_hash"],
                    output_hash=r["output_hash"],
                    safe_reason_code=r["safe_reason_code"],
                    error_details=r["error_details"]
                    if isinstance(r["error_details"], dict)
                    else (json.loads(r["error_details"]) if r["error_details"] else None),
                    created_at=r["created_at"],
                    completed_at=r["completed_at"],
                )
                for r in rows
            ]

    def _row_to_manifest(self, r: Any) -> GovernedWorkflowRunManifest:
        def _parse_json(val: Any) -> Any:
            if val is None:
                return {}
            if isinstance(val, (dict, list)):
                return val
            return json.loads(val)

        return GovernedWorkflowRunManifest(
            run_id=r["run_id"],
            manifest_hash=r["manifest_hash"],
            project_id=r["project_id"],
            workspace_id=r["workspace_id"],
            workflow_asset_id=r["workflow_asset_id"],
            workflow_version=r["workflow_version"],
            workflow_definition_hash=r["workflow_definition_hash"],
            role_deployment_id=r["role_deployment_id"],
            project_agent_deployment_id=r["project_agent_deployment_id"],
            pinned_agent_specs=_parse_json(r["pinned_agent_specs"]),
            pinned_skill_specs=_parse_json(r["pinned_skill_specs"]),
            policy_epoch=r["policy_epoch"],
            policy_hash=r["policy_hash"],
            capability_allowlist=_parse_json(r["capability_allowlist"]),
            budget_limit=_parse_json(r["budget_limit"]),
            trigger_id=r["trigger_id"],
            correlation_id=r["correlation_id"],
            evidence_refs=_parse_json(r["evidence_refs"]),
            manifest_json=_parse_json(r["manifest_json"]),
            created_at=r["created_at"],
        )
