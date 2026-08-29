"""Sync envelope — M6 §3.

Envelope (audit §5.6):
    workspace_id, entity_type, entity_id, revision, base_revision,
    source_runtime_node_id, occurred_at, idempotency_key, payload_hash,
    encryption_key_ref, encrypted_payload

- `encrypted_payload` mã hoá bằng workspace DEK (`WorkspaceKeyManager`, M3 §6) —
  platform KHÔNG thấy plaintext business payload.
- `payload_hash` = sha256 của canonical plaintext ⇒ `open_sync_envelope` verify
  toàn vẹn sau khi giải mã.
- Entity thuộc scope KHÔNG sync (credentials / transient / runs) ⇒
  `build_sync_envelope` raise `SyncScopeError`.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from agent_core.sync.scope import SyncScopeError, scope_for
from agent_core.vault.keys import WorkspaceKeyManager

__all__ = [
    "SyncEnvelope",
    "SyncEnvelopeError",
    "build_sync_envelope",
    "open_sync_envelope",
]


class SyncEnvelopeError(Exception):
    """Envelope hỏng: payload_hash lệch, giải mã thất bại, thiếu field."""


@dataclass(frozen=True)
class SyncEnvelope:
    workspace_id: str
    entity_type: str
    entity_id: str  # SpineId Snowflake | LeafId UUIDv7 — string
    revision: int
    base_revision: int
    source_runtime_node_id: str
    occurred_at: str  # ISO-8601 UTC
    idempotency_key: str
    payload_hash: str  # sha256 hex của canonical plaintext
    encryption_key_ref: str
    encrypted_payload: str  # base64(nonce + ciphertext)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "revision": self.revision,
            "base_revision": self.base_revision,
            "source_runtime_node_id": self.source_runtime_node_id,
            "occurred_at": self.occurred_at,
            "idempotency_key": self.idempotency_key,
            "payload_hash": self.payload_hash,
            "encryption_key_ref": self.encryption_key_ref,
            "encrypted_payload": self.encrypted_payload,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SyncEnvelope:
        required = (
            "workspace_id",
            "entity_type",
            "entity_id",
            "revision",
            "base_revision",
            "source_runtime_node_id",
            "occurred_at",
            "idempotency_key",
            "payload_hash",
            "encryption_key_ref",
            "encrypted_payload",
        )
        for k in required:
            if k not in d:
                raise SyncEnvelopeError(f"thiếu field {k!r}")
        return cls(
            workspace_id=str(d["workspace_id"]),
            entity_type=str(d["entity_type"]),
            entity_id=str(d["entity_id"]),
            revision=int(d["revision"]),
            base_revision=int(d["base_revision"]),
            source_runtime_node_id=str(d["source_runtime_node_id"]),
            occurred_at=str(d["occurred_at"]),
            idempotency_key=str(d["idempotency_key"]),
            payload_hash=str(d["payload_hash"]),
            encryption_key_ref=str(d["encryption_key_ref"]),
            encrypted_payload=str(d["encrypted_payload"]),
        )


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def key_ref(workspace_id: str) -> str:
    return f"workspace-dek:{workspace_id}"


def build_sync_envelope(
    *,
    workspace_id: str,
    entity_type: str,
    entity_id: str,
    revision: int,
    base_revision: int,
    source_runtime_node_id: str,
    payload: dict[str, Any],
    keys: WorkspaceKeyManager,
    occurred_at: datetime | None = None,
    idempotency_key: str | None = None,
) -> SyncEnvelope:
    policy = scope_for(entity_type)
    if not policy.syncs or policy.conflict_policy.value == "NEVER":
        raise SyncScopeError(
            f"entity_type '{entity_type}' thuộc scope {policy.scope.value} — KHÔNG sync qua kênh này"
        )
    if revision <= base_revision:
        raise SyncEnvelopeError("revision phải > base_revision")

    plaintext = _canonical(payload)
    payload_hash = hashlib.sha256(plaintext).hexdigest()
    blob = keys.encrypt(workspace_id, plaintext)
    when = (occurred_at or datetime.now(UTC)).astimezone(UTC).isoformat()

    return SyncEnvelope(
        workspace_id=workspace_id,
        entity_type=entity_type,
        entity_id=entity_id,
        revision=revision,
        base_revision=base_revision,
        source_runtime_node_id=source_runtime_node_id,
        occurred_at=when,
        idempotency_key=idempotency_key or str(uuid.uuid4()),
        payload_hash=payload_hash,
        encryption_key_ref=key_ref(workspace_id),
        encrypted_payload=base64.b64encode(blob).decode(),
    )


def open_sync_envelope(
    env: SyncEnvelope | dict[str, Any], keys: WorkspaceKeyManager
) -> dict[str, Any]:
    """Giải mã + verify `payload_hash`. Trả plaintext payload dict."""
    e = env if isinstance(env, SyncEnvelope) else SyncEnvelope.from_dict(env)
    if e.encryption_key_ref != key_ref(e.workspace_id):
        raise SyncEnvelopeError(
            f"encryption_key_ref '{e.encryption_key_ref}' không khớp workspace {e.workspace_id}"
        )
    try:
        blob = base64.b64decode(e.encrypted_payload)
        plaintext = keys.decrypt(e.workspace_id, blob)
    except Exception as exc:
        raise SyncEnvelopeError(f"giải mã encrypted_payload thất bại: {exc}") from exc

    if hashlib.sha256(plaintext).hexdigest() != e.payload_hash:
        raise SyncEnvelopeError("payload_hash lệch — payload có thể đã bị sửa")

    try:
        return json.loads(plaintext)
    except json.JSONDecodeError as exc:
        raise SyncEnvelopeError(f"payload không phải JSON hợp lệ: {exc}") from exc
