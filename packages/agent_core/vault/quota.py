"""Per-workspace storage quota — M3 §6 (phần quota).

Trục quota tách theo từng workspace (audit §6.6/§6.7): dung lượng của A vượt hạn
KHÔNG chặn B. Khác trục với `governance/budget_gate.py` (token/cost theo run) —
đây là byte trên đĩa của Vault theo workspace.

Đo `usage_bytes` = tổng kích thước file thật trong các thư mục con payload của
`workspaces/<id>/` (bỏ file metadata ở gốc như `manifest.json`, bỏ thư mục
transient `temp/`). Hạn mức lưu ở `host/catalog/quotas.json` (per-workspace,
độc lập). `assert_within()` là chốt gọi từ đường ghi (`put`, ingest, restore).

Không import `services/*`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from agent_core.vault.host_catalog import HostCatalog
from agent_core.vault.object_store import VaultSecurityError, _check_segment

__all__ = ["QuotaDecision", "QuotaExceededError", "WorkspaceStorageQuota"]

# Mặc định 5 GiB/workspace — chỉnh qua set_limit hoặc default_limit_bytes.
_DEFAULT_LIMIT_BYTES = 5 * 1024 * 1024 * 1024

# Thư mục transient không tính vào quota.
_EXCLUDED_TOP_DIRS = frozenset({"temp"})


class QuotaExceededError(Exception):
    """Ghi thêm sẽ vượt hạn mức lưu trữ của workspace."""


@dataclass
class QuotaDecision:
    workspace_id: str
    allowed: bool
    usage_bytes: int
    limit_bytes: int
    projected_bytes: int
    reason: str


class WorkspaceStorageQuota:
    def __init__(
        self,
        catalog: HostCatalog,
        *,
        default_limit_bytes: int = _DEFAULT_LIMIT_BYTES,
    ) -> None:
        self._catalog = catalog
        self._default_limit = int(default_limit_bytes)
        self._limits_file = catalog.data_root / "host" / "catalog" / "quotas.json"

    # --- limit persistence ---------------------------------------------

    def _read_limits(self) -> dict[str, int]:
        if not self._limits_file.exists():
            return {}
        return {k: int(v) for k, v in json.loads(self._limits_file.read_text()).items()}

    def _write_limits(self, limits: dict[str, int]) -> None:
        self._limits_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._limits_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(dict(sorted(limits.items())), indent=2))
        tmp.replace(self._limits_file)

    def set_limit(self, workspace_id: str, limit_bytes: int) -> None:
        _check_segment(workspace_id, field="workspace_id")
        if limit_bytes < 0:
            raise VaultSecurityError("limit_bytes không được âm")
        limits = self._read_limits()
        limits[workspace_id] = int(limit_bytes)
        self._write_limits(limits)

    def limit_for(self, workspace_id: str) -> int:
        return self._read_limits().get(workspace_id, self._default_limit)

    # --- usage ------------------------------------------------------

    def usage_bytes(self, workspace_id: str) -> int:
        ws_root = self._catalog.workspace_root(workspace_id)
        if not ws_root.exists():
            return 0
        total = 0
        for entry in ws_root.iterdir():
            # Chỉ tính thư mục con payload — bỏ file metadata ở gốc (manifest.json)
            # và thư mục transient (temp/).
            if not entry.is_dir() or entry.name in _EXCLUDED_TOP_DIRS:
                continue
            total += sum(
                p.stat().st_size for p in entry.rglob("*") if p.is_file() and not p.is_symlink()
            )
        return total

    # --- gate ------------------------------------------------------

    def check(self, workspace_id: str, incoming_bytes: int) -> QuotaDecision:
        _check_segment(workspace_id, field="workspace_id")
        if incoming_bytes < 0:
            raise VaultSecurityError("incoming_bytes không được âm")
        usage = self.usage_bytes(workspace_id)
        limit = self.limit_for(workspace_id)
        projected = usage + incoming_bytes
        allowed = projected <= limit
        reason = (
            "trong hạn mức"
            if allowed
            else (
                f"ghi thêm {incoming_bytes} byte ⇒ {projected} vượt hạn mức "
                f"{limit} byte của workspace {workspace_id}"
            )
        )
        return QuotaDecision(
            workspace_id=workspace_id,
            allowed=allowed,
            usage_bytes=usage,
            limit_bytes=limit,
            projected_bytes=projected,
            reason=reason,
        )

    def assert_within(self, workspace_id: str, incoming_bytes: int) -> QuotaDecision:
        decision = self.check(workspace_id, incoming_bytes)
        if not decision.allowed:
            raise QuotaExceededError(decision.reason)
        return decision
