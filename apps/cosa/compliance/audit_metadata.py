from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def safe_audit_metadata(
    event_type: str,
    run_context: Mapping[str, Any],
    decision: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    dec = decision or {}
    meta = {
        "event_type": event_type,
        "run_id": run_context.get("run_id"),
        "workspace_id": run_context.get("workspace_id"),
        "deployment_id": run_context.get("deployment_id"),
        "snapshot_hash": run_context.get("compliance_snapshot_ref")
        or run_context.get("snapshot_hash"),
        "reason_code": dec.get("reason_code") or dec.get("reason"),
        "capability_id": dec.get("capability_id") or run_context.get("capability_id"),
        "provider_key": dec.get("provider_key") or run_context.get("provider_key"),
    }
    return {k: v for k, v in meta.items() if v is not None}
