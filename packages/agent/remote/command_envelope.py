"""End-to-end authenticated command envelope — M5 §4.

Envelope (audit §9.5.4): `workspace_id`, `principal`, `command`, `nonce`,
`issued_at`, `expires_at`, `signature`.

- Chữ ký: HMAC-SHA256 trên canonical bytes của mọi field TRỪ `signature`, khoá
  bằng relay signing key dùng chung (device key ↔ platform — ở M5 mô hình hoá là
  shared secret; mTLS transport nằm ngoài phạm vi module này).
- Replay protection: `NonceReplayCache` (TTL theo `expires_at`) + cửa sổ
  `expires_at` kiểm ở local node. `issued_at` không được ở tương lai quá
  `_CLOCK_SKEW_SEC`.
- `verify()` trả `VerifiedCommand` mang `workspace_id` + `principal` + `command`
  ĐÃ XÁC THỰC — caller dùng cái này, KHÔNG lấy principal/workspace từ transport.

Thuần stdlib (`hmac`, `hashlib`, `json`). Không import `services/*`.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

__all__ = [
    "CommandEnvelope",
    "CommandEnvelopeVerifier",
    "EnvelopeError",
    "NonceReplayCache",
    "Principal",
    "VerifiedCommand",
    "canonical_bytes",
    "sign_envelope",
]

# Cho phép issued_at lệch tối đa từng này giây về tương lai (clock skew relay/node).
_CLOCK_SKEW_SEC = 60
# Trần TTL của một envelope — chặn nonce phải giữ trong cache quá lâu.
_MAX_TTL_SEC = 15 * 60

PrincipalKind = Literal["user", "workforce_member"]


class EnvelopeError(Exception):
    """Envelope không hợp lệ: sai chữ ký, hết hạn, replay, thiếu field, …."""


@dataclass(frozen=True)
class Principal:
    kind: PrincipalKind
    id: str

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "id": self.id}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Principal:
        kind = d.get("kind")
        if kind not in ("user", "workforce_member"):
            raise EnvelopeError(f"principal.kind không hợp lệ: {kind!r}")
        pid = d.get("id")
        if not isinstance(pid, str) or not pid:
            raise EnvelopeError("principal.id rỗng/không hợp lệ")
        return cls(kind=kind, id=pid)


@dataclass(frozen=True)
class CommandEnvelope:
    workspace_id: str
    principal: Principal
    command: dict[str, Any]
    nonce: str
    issued_at: str  # ISO-8601 UTC
    expires_at: str  # ISO-8601 UTC
    signature: str = ""  # base64 hex HMAC — rỗng khi chưa ký

    def signing_payload(self) -> dict[str, Any]:
        """Field dùng để ký (mọi thứ trừ `signature`)."""
        return {
            "workspace_id": self.workspace_id,
            "principal": self.principal.to_dict(),
            "command": self.command,
            "nonce": self.nonce,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.signing_payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CommandEnvelope:
        for field in ("workspace_id", "nonce", "issued_at", "expires_at"):
            if not isinstance(d.get(field), str) or not d[field]:
                raise EnvelopeError(f"thiếu/không hợp lệ field {field!r}")
        command = d.get("command")
        if not isinstance(command, dict):
            raise EnvelopeError("command phải là object")
        return cls(
            workspace_id=d["workspace_id"],
            principal=Principal.from_dict(d.get("principal") or {}),
            command=command,
            nonce=d["nonce"],
            issued_at=d["issued_at"],
            expires_at=d["expires_at"],
            signature=d.get("signature", "") or "",
        )


@dataclass(frozen=True)
class VerifiedCommand:
    """Kết quả xác thực — principal/workspace ở đây là nguồn sự thật."""

    workspace_id: str
    principal: Principal
    command: dict[str, Any]
    nonce: str
    expires_at: datetime


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    """JSON tất định: sort key, không khoảng trắng thừa, UTF-8. Cùng một payload ⇒
    cùng bytes ⇒ cùng chữ ký ở producer và verifier."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _hmac_hex(key: bytes, payload: dict[str, Any]) -> str:
    return hmac.new(key, canonical_bytes(payload), hashlib.sha256).hexdigest()


def sign_envelope(envelope: CommandEnvelope, signing_key: bytes) -> CommandEnvelope:
    """Trả về bản sao envelope có `signature` (dùng ở producer / test)."""
    sig = _hmac_hex(signing_key, envelope.signing_payload())
    return CommandEnvelope(
        workspace_id=envelope.workspace_id,
        principal=envelope.principal,
        command=envelope.command,
        nonce=envelope.nonce,
        issued_at=envelope.issued_at,
        expires_at=envelope.expires_at,
        signature=sig,
    )


def _parse_iso_utc(value: str, *, field: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise EnvelopeError(f"{field} không phải ISO-8601: {value!r}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class NonceReplayCache:
    """Cache nonce đã tiêu, TTL theo `expires_at` (giữ đến khi envelope hết hạn là
    đủ — sau đó cửa sổ `expires_at` tự chặn). Bind theo `(workspace_id, nonce)`."""

    def __init__(self) -> None:
        self._seen: dict[tuple[str, str], float] = {}

    def _evict(self, now: float) -> None:
        expired = [k for k, exp in self._seen.items() if exp <= now]
        for k in expired:
            del self._seen[k]

    def check_and_record(
        self, workspace_id: str, nonce: str, expires_at_epoch: float, *, now: float | None = None
    ) -> None:
        n = time.time() if now is None else now
        self._evict(n)
        key = (workspace_id, nonce)
        if key in self._seen:
            raise EnvelopeError("nonce đã được dùng (replay bị chặn)")
        self._seen[key] = expires_at_epoch

    def __len__(self) -> int:  # pragma: no cover - tiện debug/test
        return len(self._seen)


class CommandEnvelopeVerifier:
    """Xác thực envelope ở local node: chữ ký → hạn → clock skew → replay."""

    def __init__(
        self,
        signing_key: bytes,
        *,
        nonce_cache: NonceReplayCache | None = None,
        clock_skew_sec: int = _CLOCK_SKEW_SEC,
        max_ttl_sec: int = _MAX_TTL_SEC,
    ) -> None:
        if not signing_key:
            raise EnvelopeError("signing_key rỗng")
        self._key = signing_key
        self._nonces = nonce_cache or NonceReplayCache()
        self._skew = clock_skew_sec
        self._max_ttl = max_ttl_sec

    def verify(
        self, envelope: CommandEnvelope | dict[str, Any], *, now: datetime | None = None
    ) -> VerifiedCommand:
        env = (
            envelope
            if isinstance(envelope, CommandEnvelope)
            else CommandEnvelope.from_dict(envelope)
        )
        current = (now or datetime.now(UTC)).astimezone(UTC)

        # 1. Chữ ký — so sánh constant-time.
        if not env.signature:
            raise EnvelopeError("thiếu signature")
        expected = _hmac_hex(self._key, env.signing_payload())
        if not hmac.compare_digest(expected, env.signature):
            raise EnvelopeError("chữ ký không hợp lệ")

        # 2. Hạn dùng.
        issued = _parse_iso_utc(env.issued_at, field="issued_at")
        expires = _parse_iso_utc(env.expires_at, field="expires_at")
        if expires <= issued:
            raise EnvelopeError("expires_at phải sau issued_at")
        if (expires - issued).total_seconds() > self._max_ttl:
            raise EnvelopeError(f"TTL envelope vượt trần {self._max_ttl}s")
        if current >= expires:
            raise EnvelopeError("envelope đã hết hạn")
        if issued - current > timedelta(seconds=self._skew):
            raise EnvelopeError("issued_at ở tương lai quá cửa sổ clock-skew")

        # 3. Replay.
        self._nonces.check_and_record(
            env.workspace_id, env.nonce, expires.timestamp(), now=current.timestamp()
        )

        return VerifiedCommand(
            workspace_id=env.workspace_id,
            principal=env.principal,
            command=env.command,
            nonce=env.nonce,
            expires_at=expires,
        )
