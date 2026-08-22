from __future__ import annotations

import enum


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
    """Deterministic ALLOW/DENY/REQUIRE_APPROVAL gate (blueprint §50) — a
    policy decision is code, never an LLM judgment call (CLAUDE.md §11 /
    blueprint §11). The default table follows the blueprint §86 MVP
    autonomy defaults: read/analysis auto-allow; external communication,
    business-data writes, delete, finance, deploy, and code execution
    require approval; secret access is denied outright.
    """

    def __init__(self, table: dict[PermissionClass, PolicyDecision] | None = None) -> None:
        self._table = dict(table) if table is not None else dict(DEFAULT_POLICY_TABLE)

    def evaluate(self, permission: PermissionClass) -> PolicyDecision:
        return self._table.get(permission, PolicyDecision.REQUIRE_APPROVAL)
