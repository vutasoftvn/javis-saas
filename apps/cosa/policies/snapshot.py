from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "AgentAuthorizationSnapshot",
    "AgentCapabilityAuthority",
    "BusinessPermissionRule",
    "BusinessPolicyRuleSet",
    "PolicySnapshot",
    "TenantPolicyRule",
]


class TenantPolicyRule(BaseModel):
    """Khớp 1 row `cosa.company_agent_policy`."""

    tool_pattern: str
    decision: str  # ALLOW | REQUIRE_APPROVAL | DENY
    reason: str | None = None


class BusinessPermissionRule(BaseModel):
    """IA02 phần 2 — khớp 1 row `core.role_permissions` (services/company,
    permission-catalog.ts). Port trực tiếp từ PermissionRule
    (identity/services/permission-evaluator.ts) — permission_key CHỈ nhận
    giá trị đã đăng ký trong PERMISSION_CATALOG (FK constraint thật ở DB),
    không phải capability_id tuỳ ý phía Python."""

    permission_key: str
    effect: str  # ALLOW | DENY | REQUIRE_APPROVAL
    conditions: dict[str, Any] = Field(default_factory=dict)


class AgentCapabilityAuthority(BaseModel):
    capability_id: str
    permission_key: str
    risk_class: str
    grant_id: str
    constraints: dict[str, Any] = Field(default_factory=dict)


class AgentAuthorizationSnapshot(BaseModel):
    authorization_epoch: int = 1
    grants: list[AgentCapabilityAuthority] = Field(default_factory=list)

    def resolve(
        self, capability_id: str, payload: dict[str, Any] | None = None
    ) -> tuple[bool, str, AgentCapabilityAuthority | None]:
        matched = [g for g in self.grants if g.capability_id == capability_id]
        if not matched:
            return False, "MISSING_AGENT_CAPABILITY_GRANT", None
        grant = matched[0]
        constraints = grant.constraints or {}
        if "maxAmountMinor" in constraints and payload:
            facts_amount = payload.get("amount")
            if facts_amount is None:
                return False, "MISSING_REQUIRED_FACT_AMOUNT", grant
            minor = facts_amount.get("minor") if isinstance(facts_amount, dict) else facts_amount
            if minor is not None and int(minor) > int(constraints["maxAmountMinor"]):
                return False, "CONSTRAINT_AMOUNT_EXCEEDED", grant
        if "currency" in constraints and payload:
            facts_amount = payload.get("amount")
            if isinstance(facts_amount, dict) and facts_amount.get("currency") != constraints["currency"]:
                return False, "CONSTRAINT_CURRENCY_MISMATCH", grant
        return True, "ALLOWED", grant


class BusinessPolicyRuleSet(BaseModel):
    """IA02 phần 2 — kết quả GET /identity/business-policy/rules. rule_groups
    nhóm theo TỪNG role assignment (không flatten) để tái tạo đúng thuật
    toán combine_permission_rules gốc (xem business_permission_evaluator.py)."""

    is_founder: bool = False
    policy_version: int = 1
    authorization_epoch: int = 1
    rule_groups: list[list[BusinessPermissionRule]] = Field(default_factory=list)
    agent_capabilities: list[AgentCapabilityAuthority] = Field(default_factory=list)


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

    workspace_id: str
    workspace_status: str
    principal_status: str
    rules: list[TenantPolicyRule]
    snapshot_hash: str
    business_policy_ref: dict[str, Any] | None = None
    agent_authority: AgentAuthorizationSnapshot | None = None
    # IA02 phần 2 — raw rule set từ services/company (GET
    # /identity/business-policy/rules), resolve CÙNG lúc với snapshot ở
    # boundary run-start/trước resume. None = chưa fetch được/không áp dụng
    # (fail-open cho bước NÀY — chỉ ảnh hưởng business_policy check ở
    # evaluator.py, không ảnh hưởng workspace_status/principal_status/
    # snapshot.match() vốn vẫn là các gate chính).
    business_policy_rules: BusinessPolicyRuleSet | None = None

    def match(self, capability_id: str) -> TenantPolicyRule | None:
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
    def from_context(cls, context: dict[str, Any]) -> PolicySnapshot | None:
        raw = context.get("policy_snapshot")
        if raw is None:
            return None
        if isinstance(raw, PolicySnapshot):
            return raw
        return cls.model_validate(raw)
