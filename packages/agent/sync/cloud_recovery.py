"""Cloud runtime recovery guards — M6 §5/§6.

Khi cloud runtime tiếp quản một workspace:
- Thiếu workspace DEK ⇒ FAIL-CLOSED + hướng dẫn recovery. TUYỆT ĐỐI KHÔNG tạo
  vault/DEK rỗng mới cùng ID (guardrail — sẽ mất khả năng giải mã dữ liệu cũ).
- Connector chỉ có credential local (không có cloud-scoped secret) ⇒ capability
  đánh dấu `MISSING_CREDENTIAL`, KHÔNG giả lập thành công (§6: grant handle sync
  được, secret material thì không).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

__all__ = [
    "CapabilityAvailability",
    "CloudRecoveryError",
    "ConnectorGrantView",
    "assert_workspace_key_present",
    "classify_connector_availability",
]


class CloudRecoveryError(Exception):
    """Cloud runtime không thể tiếp quản an toàn (thiếu key, …)."""


class _WrappedDekProvider(Protocol):
    def export_wrapped_dek(self, workspace_id: str) -> str: ...


def assert_workspace_key_present(workspace_id: str, keys: _WrappedDekProvider) -> None:
    """FAIL-CLOSED nếu workspace chưa có DEK ở cloud host. KHÔNG gọi `ensure_dek`
    (không được tự tạo key mới) — chỉ kiểm tra và hướng dẫn recovery."""
    try:
        wrapped = keys.export_wrapped_dek(workspace_id)
    except Exception as exc:
        raise CloudRecoveryError(
            f"workspace {workspace_id} chưa có DEK trên cloud host — KHÔNG tạo vault rỗng mới. "
            "Recovery: khôi phục wrapped DEK từ backup/export (M3 §9) hoặc từ local node "
            "trước khi cho cloud runtime tiếp quản."
        ) from exc
    if not wrapped:
        raise CloudRecoveryError(
            f"wrapped DEK của workspace {workspace_id} rỗng — fail-closed, cần recovery"
        )


class CapabilityAvailability(StrEnum):
    READY = "READY"
    MISSING_CREDENTIAL = "MISSING_CREDENTIAL"


@dataclass(frozen=True)
class ConnectorGrantView:
    connector_key: str
    # handle được sync (không phải secret). None ⇒ chưa có grant.
    grant_handle: str | None
    # secret material cấp riêng cho cloud (KHÔNG copy từ local). False ⇒ chỉ local.
    cloud_secret_provisioned: bool

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ConnectorGrantView:
        return cls(
            connector_key=str(d.get("connector_key") or d.get("connectorKey") or ""),
            grant_handle=(d.get("grant_handle") or d.get("grantHandle")) or None,
            cloud_secret_provisioned=bool(
                d.get("cloud_secret_provisioned") or d.get("cloudSecretProvisioned")
            ),
        )


def classify_connector_availability(grant: ConnectorGrantView) -> CapabilityAvailability:
    """`READY` chỉ khi có grant handle VÀ secret material đã cấp riêng cho cloud.
    Có handle nhưng thiếu cloud secret (credential chỉ nằm ở local) ⇒
    `MISSING_CREDENTIAL` — cloud runtime KHÔNG giả lập thành công."""
    if grant.grant_handle and grant.cloud_secret_provisioned:
        return CapabilityAvailability.READY
    return CapabilityAvailability.MISSING_CREDENTIAL
