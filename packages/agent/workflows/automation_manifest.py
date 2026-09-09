"""COSA Automation MVP (Task 5) — the immutable execution manifest pinned before
a curated automation run enters RUNNING.

docs/superpowers/specs/2026-09-10-cosa-automation-mvp-design.md §4.2.

The manifest is resolved once from the opaque dispatch payload + the registered
blueprint, hash-verified, and persisted insert-once. Retry / resume / reclaim
reload it by run_id and compare `manifest_hash` — they never silently resolve a
newer blueprint or policy. Because the effective policy is pinned at publish
time on the Company revision, the manifest IS the policy snapshot for an
automation run: an automation run does not call the Control Plane policy-snapshot
endpoint.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from agent.governance.hashing import definition_hash
from agent.workflows.schema import WorkflowSpec

__all__ = [
    "AutomationExecutionManifest",
    "AutomationManifestError",
    "resolve_automation_manifest",
]


class AutomationManifestError(Exception):
    """Raised when a dispatch cannot be pinned to a known, hash-matching blueprint."""


class AutomationExecutionManifest(BaseModel):
    """Reference-only. No raw business content, prompt, credential or grant."""

    model_config = {"frozen": True}

    run_id: str
    invocation_id: str
    workspace_id: str
    automation_key: str
    revision: int
    revision_hash: str
    blueprint_version: str
    blueprint_hash: str
    pinned_agent_spec_id: str
    capability_allowlist: tuple[str, ...] = ()
    autonomy_class: str = "read_only"
    approval_required: bool = False
    evidence_requires: tuple[str, ...] = ()
    trigger_kind: str = "manual"
    trigger_identity: str = ""
    correlation_id: str = ""
    runtime_requirement: str = "any"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def compute_hash(self) -> str:
        data = self.model_dump(exclude={"created_at"}, mode="json")
        return definition_hash(data)


def resolve_automation_manifest(
    *,
    dispatch_payload: dict[str, Any],
    blueprint_spec: WorkflowSpec,
    blueprint_metadata: dict[str, Any],
) -> AutomationExecutionManifest:
    """Build the manifest from the opaque dispatch payload and the registered
    blueprint. `blueprint_metadata` carries the curated capability allowlist /
    autonomy / evidence / pinned spec (source of truth: the Company revision,
    mirrored on the Agent side by automation_blueprints.py)."""
    required = (
        "run_id",
        "invocation_id",
        "workspace_id",
        "automation_key",
        "revision",
        "revision_hash",
    )
    for key in required:
        if not dispatch_payload.get(key):
            raise AutomationManifestError(f"dispatch payload missing '{key}'")

    key = dispatch_payload["automation_key"]
    if blueprint_spec.id != key:
        raise AutomationManifestError(
            f"blueprint spec id '{blueprint_spec.id}' does not match automation_key '{key}'"
        )

    blueprint_hash = blueprint_spec.definition_hash or blueprint_spec.compute_hash()

    return AutomationExecutionManifest(
        run_id=str(dispatch_payload["run_id"]),
        invocation_id=str(dispatch_payload["invocation_id"]),
        workspace_id=str(dispatch_payload["workspace_id"]),
        automation_key=key,
        revision=int(dispatch_payload["revision"]),
        revision_hash=str(dispatch_payload["revision_hash"]),
        blueprint_version=blueprint_spec.version,
        blueprint_hash=blueprint_hash,
        pinned_agent_spec_id=str(blueprint_metadata["pinned_agent_spec_id"]),
        capability_allowlist=tuple(blueprint_metadata.get("capability_ids", ())),
        autonomy_class=str(blueprint_metadata.get("autonomy_class", "read_only")),
        approval_required=bool(blueprint_metadata.get("approval_required", False)),
        evidence_requires=tuple(blueprint_metadata.get("evidence_requires", ())),
        trigger_kind=str(dispatch_payload.get("trigger_kind", "manual")),
        trigger_identity=str(dispatch_payload.get("trigger_identity", "")),
        correlation_id=str(dispatch_payload.get("correlation_id", "")),
        runtime_requirement=str(blueprint_metadata.get("runtime_requirement", "any")),
    )
