"""Encrypted selective sync theo aggregate — M6 §3.

KHÔNG replicate DB row trực tiếp. Mọi thay đổi đi qua `SyncEnvelope` (revision +
base_revision + payload_hash + encrypted_payload). Encryption bằng workspace DEK
(M3 §6) — platform KHÔNG giữ plaintext key và KHÔNG thấy plaintext business payload.

Sync scope (audit §5.6):
- control metadata: sync khi link platform, optimistic.
- business modules: opt-in theo module, optimistic.
- finance/legal / approval / lifecycle / policy: revision-based, conflict CẦN
  human resolve — KHÔNG generic last-write-wins (guardrail 8).
- credentials: KHÔNG sync raw secret (chỉ connector grant handle).
- runs/memory/artifacts: local mặc định (optional backup riêng).
- quarantine/temp/cache: KHÔNG sync.

Không import `services/*`.
"""

from agent_core.sync.cloud_recovery import (
    CapabilityAvailability,
    CloudRecoveryError,
    ConnectorGrantView,
    assert_workspace_key_present,
    classify_connector_availability,
)
from agent_core.sync.conflict import (
    ConflictResolution,
    SyncConflictError,
    resolve_incoming_revision,
    write_conflict_entry,
)
from agent_core.sync.envelope import (
    SyncEnvelope,
    SyncEnvelopeError,
    build_sync_envelope,
    open_sync_envelope,
)
from agent_core.sync.scope import (
    ConflictPolicy,
    SyncScope,
    SyncScopeError,
    SyncScopePolicy,
    scope_for,
)

__all__ = [
    "CapabilityAvailability",
    "CloudRecoveryError",
    "ConflictPolicy",
    "ConflictResolution",
    "ConnectorGrantView",
    "SyncConflictError",
    "SyncEnvelope",
    "SyncEnvelopeError",
    "SyncScope",
    "SyncScopeError",
    "SyncScopePolicy",
    "assert_workspace_key_present",
    "build_sync_envelope",
    "classify_connector_availability",
    "open_sync_envelope",
    "resolve_incoming_revision",
    "scope_for",
    "write_conflict_entry",
]
