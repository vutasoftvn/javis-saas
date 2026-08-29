"""Conflict recovery — M6 §4/§5.

Revision-based reconcile. KHÔNG generic last-write-wins cho critical data
(guardrail 8): finance/legal/approval/lifecycle/policy diverge ⇒ đưa vào
`sync/conflicts/` + human resolve, giữ đủ audit hai phía.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from agent_core.sync.envelope import SyncEnvelope
from agent_core.sync.scope import ConflictPolicy, scope_for

__all__ = [
    "ConflictResolution",
    "SyncConflictError",
    "resolve_incoming_revision",
    "write_conflict_entry",
]


class SyncConflictError(Exception):
    """Không thể reconcile tự động (scope NEVER, hoặc dữ liệu conflict thiếu)."""


class ConflictResolution(StrEnum):
    APPLY = "APPLY"  # fast-forward: base_revision == current_revision
    IGNORE_STALE = "IGNORE_STALE"  # incoming.revision <= current — đã có bản mới hơn/bằng
    APPLY_WITH_AUDIT = "APPLY_WITH_AUDIT"  # optimistic diverge — apply nhưng GHI audit hai phía
    QUEUE_CONFLICT = "QUEUE_CONFLICT"  # critical diverge — KHÔNG tự merge, chờ human


def resolve_incoming_revision(
    *, incoming: SyncEnvelope, current_revision: int
) -> ConflictResolution:
    policy = scope_for(incoming.entity_type)
    if policy.conflict_policy == ConflictPolicy.NEVER:
        raise SyncConflictError(
            f"entity_type '{incoming.entity_type}' thuộc scope không sync — không reconcile"
        )

    if incoming.revision <= current_revision:
        return ConflictResolution.IGNORE_STALE
    if incoming.base_revision == current_revision:
        return ConflictResolution.APPLY

    # diverged: base_revision < current_revision < incoming.revision
    if policy.conflict_policy == ConflictPolicy.HUMAN_RESOLVE:
        return ConflictResolution.QUEUE_CONFLICT
    return ConflictResolution.APPLY_WITH_AUDIT


@dataclass(frozen=True)
class _ConflictRecord:
    workspace_id: str
    entity_type: str
    entity_id: str
    incoming_revision: int
    incoming_base_revision: int
    current_revision: int
    source_runtime_node_id: str
    incoming_payload_hash: str
    local_payload_hash: str | None
    detected_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "incoming_revision": self.incoming_revision,
            "incoming_base_revision": self.incoming_base_revision,
            "current_revision": self.current_revision,
            "source_runtime_node_id": self.source_runtime_node_id,
            "incoming_payload_hash": self.incoming_payload_hash,
            "local_payload_hash": self.local_payload_hash,
            "detected_at": self.detected_at,
            "status": "AWAITING_HUMAN_RESOLVE",
        }


def write_conflict_entry(
    conflicts_dir: str | os.PathLike[str],
    *,
    incoming: SyncEnvelope,
    current_revision: int,
    local_payload_hash: str | None,
) -> Path:
    """Ghi 1 file conflict vào `sync/conflicts/` (đủ audit hai phía, KHÔNG chứa
    plaintext payload — chỉ hash + metadata). Trả path file đã ghi."""
    d = Path(conflicts_dir)
    d.mkdir(parents=True, exist_ok=True)
    rec = _ConflictRecord(
        workspace_id=incoming.workspace_id,
        entity_type=incoming.entity_type,
        entity_id=incoming.entity_id,
        incoming_revision=incoming.revision,
        incoming_base_revision=incoming.base_revision,
        current_revision=current_revision,
        source_runtime_node_id=incoming.source_runtime_node_id,
        incoming_payload_hash=incoming.payload_hash,
        local_payload_hash=local_payload_hash,
        detected_at=datetime.now(UTC).isoformat(),
    )
    safe_entity = "".join(c if c.isalnum() or c in "._-" else "_" for c in incoming.entity_id)
    path = d / f"{incoming.entity_type}__{safe_entity}__r{incoming.revision}.json"
    path.write_text(json.dumps(rec.to_dict(), indent=2))
    return path
