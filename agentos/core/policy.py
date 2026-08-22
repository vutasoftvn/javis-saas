from __future__ import annotations

import enum

from agentos.core.audit_sink import AuditSink


class PermissionClass(str, enum.Enum):
    READ_LOCAL = "READ_LOCAL"
    WRITE_WORKSPACE = "WRITE_WORKSPACE"
    READ_NETWORK = "READ_NETWORK"
    EXTERNAL_WRITE = "EXTERNAL_WRITE"
    SEND_MESSAGE = "SEND_MESSAGE"
    MODIFY_BUSINESS_DATA = "MODIFY_BUSINESS_DATA"
    DEPLOY = "DEPLOY"
    EXECUTE_CODE = "EXECUTE_CODE"
    ACCESS_SECRET = "ACCESS_SECRET"
    DELETE_DATA = "DELETE_DATA"
    FINANCIAL_ACTION = "FINANCIAL_ACTION"


class PolicyDecision(str, enum.Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


DEFAULT_POLICY_TABLE: dict[PermissionClass, PolicyDecision] = {
    PermissionClass.READ_LOCAL: PolicyDecision.ALLOW,
    PermissionClass.WRITE_WORKSPACE: PolicyDecision.ALLOW,
    PermissionClass.READ_NETWORK: PolicyDecision.ALLOW,
    PermissionClass.EXTERNAL_WRITE: PolicyDecision.REQUIRE_APPROVAL,
    PermissionClass.SEND_MESSAGE: PolicyDecision.REQUIRE_APPROVAL,
    PermissionClass.MODIFY_BUSINESS_DATA: PolicyDecision.REQUIRE_APPROVAL,
    PermissionClass.DEPLOY: PolicyDecision.REQUIRE_APPROVAL,
    PermissionClass.EXECUTE_CODE: PolicyDecision.REQUIRE_APPROVAL,
    PermissionClass.ACCESS_SECRET: PolicyDecision.DENY,
    PermissionClass.DELETE_DATA: PolicyDecision.REQUIRE_APPROVAL,
    PermissionClass.FINANCIAL_ACTION: PolicyDecision.REQUIRE_APPROVAL,
}


class PolicyEngine:
    """Cổng quyết định ALLOW/DENY/REQUIRE_APPROVAL tất định (blueprint §50)
    — quyết định permission luôn là code, không bao giờ là phán đoán của LLM
    (CLAUDE.md §11 / blueprint §11). Bảng mặc định theo đúng autonomy default
    của blueprint §86 MVP: read/analysis auto-allow; external communication,
    ghi business-data, delete, finance, deploy, execute code cần approval;
    truy cập secret bị deny thẳng.

    `audit_sink` (tùy chọn) ghi bền vững mọi quyết định (gap analysis Giai
    đoạn 3.4 — trước đây PolicyEngine không để lại audit trail nào ngoài
    trace của riêng 1 run).
    """

    def __init__(
        self,
        table: dict[PermissionClass, PolicyDecision] | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._table = dict(table) if table is not None else dict(DEFAULT_POLICY_TABLE)
        self._audit_sink = audit_sink

    def evaluate(self, permission: PermissionClass, *, run_id: str | None = None) -> PolicyDecision:
        decision = self._table.get(permission, PolicyDecision.REQUIRE_APPROVAL)
        if self._audit_sink is not None:
            self._audit_sink.record(
                event_type="policy.evaluated",
                run_id=run_id,
                subject=permission.value,
                decision=decision.value,
            )
        return decision
