"""Relay command gate — M5 §4 (audit side).

Local node nhận command envelope đã relay ⇒ `RelayCommandGate.accept()`:
1. xác thực envelope (`CommandEnvelopeVerifier`)
2. GHI AUDIT vào local audit log — cả khi ACCEPTED lẫn REJECTED — với `principal`
   (từ envelope đã xác thực, KHÔNG từ transport) + `source="remote_relay"`
3. trả `VerifiedCommand` để dispatch, hoặc raise `EnvelopeError`

Không import `services/*`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from agent.remote.command_envelope import (
    CommandEnvelope,
    CommandEnvelopeVerifier,
    EnvelopeError,
    Principal,
    VerifiedCommand,
)

__all__ = [
    "InMemoryAuditSink",
    "RelayCommandGate",
    "RemoteCommandAudit",
    "RemoteCommandAuditSink",
]

AuditOutcome = Literal["accepted", "rejected"]


@dataclass(frozen=True)
class RemoteCommandAudit:
    workspace_id: str
    principal: Principal | None  # None khi envelope hỏng đến mức không đọc được principal
    command: dict[str, Any] | None
    nonce: str | None
    received_at: str  # ISO-8601 UTC
    outcome: AuditOutcome
    source: str = "remote_relay"
    reject_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "principal": self.principal.to_dict() if self.principal else None,
            "command": self.command,
            "nonce": self.nonce,
            "received_at": self.received_at,
            "outcome": self.outcome,
            "source": self.source,
            "reject_reason": self.reject_reason,
        }


class RemoteCommandAuditSink(ABC):
    @abstractmethod
    def record(self, entry: RemoteCommandAudit) -> None: ...


class InMemoryAuditSink(RemoteCommandAuditSink):
    def __init__(self) -> None:
        self.entries: list[RemoteCommandAudit] = []

    def record(self, entry: RemoteCommandAudit) -> None:
        self.entries.append(entry)


class RelayCommandGate:
    def __init__(
        self, verifier: CommandEnvelopeVerifier, audit_sink: RemoteCommandAuditSink
    ) -> None:
        self._verifier = verifier
        self._audit = audit_sink

    def accept(
        self, raw_envelope: CommandEnvelope | dict[str, Any], *, now: datetime | None = None
    ) -> VerifiedCommand:
        received = (now or datetime.now(UTC)).astimezone(UTC).isoformat()

        # Thử đọc workspace/principal thô để audit kể cả khi verify fail (không tin
        # các giá trị này — chỉ để có dòng log; giá trị tin cậy nằm ở VerifiedCommand).
        raw_ws, raw_principal, raw_command, raw_nonce = _peek(raw_envelope)

        try:
            verified = self._verifier.verify(raw_envelope, now=now)
        except EnvelopeError as exc:
            self._audit.record(
                RemoteCommandAudit(
                    workspace_id=raw_ws or "?",
                    principal=raw_principal,
                    command=raw_command,
                    nonce=raw_nonce,
                    received_at=received,
                    outcome="rejected",
                    reject_reason=str(exc),
                )
            )
            raise

        self._audit.record(
            RemoteCommandAudit(
                workspace_id=verified.workspace_id,
                principal=verified.principal,
                command=verified.command,
                nonce=verified.nonce,
                received_at=received,
                outcome="accepted",
            )
        )
        return verified


def _peek(
    raw: CommandEnvelope | dict[str, Any],
) -> tuple[str | None, Principal | None, dict[str, Any] | None, str | None]:
    if isinstance(raw, CommandEnvelope):
        return raw.workspace_id, raw.principal, raw.command, raw.nonce
    ws = raw.get("workspace_id") if isinstance(raw, dict) else None
    nonce = raw.get("nonce") if isinstance(raw, dict) else None
    command = raw.get("command") if isinstance(raw, dict) else None
    principal: Principal | None = None
    try:
        p = raw.get("principal") if isinstance(raw, dict) else None
        if isinstance(p, dict):
            principal = Principal.from_dict(p)
    except EnvelopeError:
        principal = None
    return (
        ws if isinstance(ws, str) else None,
        principal,
        command if isinstance(command, dict) else None,
        nonce if isinstance(nonce, str) else None,
    )
