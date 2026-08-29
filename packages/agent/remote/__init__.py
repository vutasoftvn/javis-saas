"""Remote Access primitives (M5) — chạy ở Local Workspace Runtime Node.

`REMOTE_ACCESS`: business data vẫn ở local; platform chỉ route encrypted command
envelope. Local node là nơi xác thực envelope (chữ ký + hạn + chống replay) —
`principal`/`workspace_id` trong envelope là NGUỒN SỰ THẬT, không suy từ transport.

Không import `services/*`.
"""

from agent.remote.command_envelope import (
    CommandEnvelope,
    CommandEnvelopeVerifier,
    EnvelopeError,
    NonceReplayCache,
    Principal,
    VerifiedCommand,
    canonical_bytes,
    sign_envelope,
)
from agent.remote.relay_command_gate import (
    InMemoryAuditSink,
    RelayCommandGate,
    RemoteCommandAudit,
    RemoteCommandAuditSink,
)

__all__ = [
    "CommandEnvelope",
    "CommandEnvelopeVerifier",
    "EnvelopeError",
    "InMemoryAuditSink",
    "NonceReplayCache",
    "Principal",
    "RelayCommandGate",
    "RemoteCommandAudit",
    "RemoteCommandAuditSink",
    "VerifiedCommand",
    "canonical_bytes",
    "sign_envelope",
]
