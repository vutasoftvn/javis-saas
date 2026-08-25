from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

__all__ = ["TenantPolicyRule", "PolicySnapshot"]


class TenantPolicyRule(BaseModel):
    """Khớp 1 row `cosa.company_agent_policy`."""

    tool_pattern: str
    decision: str  # ALLOW | REQUIRE_APPROVAL | DENY
    reason: Optional[str] = None


class PolicySnapshot(BaseModel):
    """Snapshot của `cosa.company_agent_policy` + current gate tại thời điểm
    resolve (run-start hoặc trước resume) — theo
    COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §29.3 mục 1:
    "Wire canonical tenant-policy storage into the already-wired runtime
    evaluator", không phải tạo policy engine thứ hai.

    `snapshot_hash` persist vào context để audit/replay biết đúng snapshot
    nào đã dùng cho quyết định — resolve tại `services/cosa` (nguồn sự thật),
    không tính hash phía Python để tránh lệch nếu logic 2 bên trôi nhau.
    """

    company_id: str
    company_status: str
    principal_status: str
    rules: list[TenantPolicyRule]
    snapshot_hash: str

    def match(self, capability_id: str) -> Optional[TenantPolicyRule]:
        """Cùng thứ tự ưu tiên với `getTenantPolicyForTool` trong
        services/cosa/services/agent-policy.service.ts: exact -> prefix
        wildcard (dài nhất trước) -> `*`."""
        exact = next((r for r in self.rules if r.tool_pattern == capability_id), None)
        if exact is not None:
            return exact

        prefix_matches = [
            r
            for r in self.rules
            if r.tool_pattern.endswith(".*") and capability_id.startswith(r.tool_pattern[:-1])
        ]
        if prefix_matches:
            return max(prefix_matches, key=lambda r: len(r.tool_pattern))

        return next((r for r in self.rules if r.tool_pattern == "*"), None)

    @classmethod
    def from_context(cls, context: dict[str, Any]) -> Optional["PolicySnapshot"]:
        raw = context.get("policy_snapshot")
        if raw is None:
            return None
        if isinstance(raw, PolicySnapshot):
            return raw
        return cls.model_validate(raw)
