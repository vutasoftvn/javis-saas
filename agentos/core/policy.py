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


class ToolRiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolPermission(str, enum.Enum):
    READ_ONLY = "read_only"
    SCOPED_WRITE = "scoped_write"
    ADMIN_WRITE = "admin_write"


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
        self._custom_overrides = set(table.keys()) if table is not None else set()
        self._table = dict(table) if table is not None else dict(DEFAULT_POLICY_TABLE)
        self._audit_sink = audit_sink

    def evaluate_access(
        self,
        *,
        role: str,
        agent_permission_level: PermissionLevel,
        tool_risk_level: ToolRiskLevel,
        tool_permission: ToolPermission,
        tenant_policy: TenantPolicyDecision | None = None,
        execution_mode: ExecutionMode | None = None,
        data_scope: DataScope | None = None,
        run_id: str | None = None,
        permission_class: PermissionClass | None = None,
        approval_policy: str | None = None,
        correlation_id: str | None = None,
        workspace_id: str | None = None,
        company_id: str | None = None,
    ) -> PolicyDecision:
        if permission_class is not None and permission_class in self._custom_overrides:
            decision = self._table[permission_class]
        else:
            decision = evaluate_access(
                role=role,
                agent_permission_level=agent_permission_level,
                tool_risk_level=tool_risk_level,
                tool_permission=tool_permission,
                tenant_policy=tenant_policy,
                execution_mode=execution_mode,
                data_scope=data_scope,
                approval_policy=approval_policy,
            )
            if permission_class == PermissionClass.ACCESS_SECRET and role not in ("founder", "admin"):
                decision = PolicyDecision.DENY

        if self._audit_sink is not None:
            self._audit_sink.record(
                event_type="policy.evaluated",
                run_id=run_id,
                subject=permission_class.value if permission_class else f"{role}:{tool_risk_level.value if isinstance(tool_risk_level, ToolRiskLevel) else tool_risk_level}:{tool_permission.value if isinstance(tool_permission, ToolPermission) else tool_permission}",
                decision=decision.value,
            )
        return decision

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

    def evaluate_for_agent(
        self,
        *,
        agent_permission_level: "PermissionLevel",
        tool_risk_level: str,
        tool_permission: str,
        run_id: str | None = None,
    ) -> PolicyDecision:
        """Mô hình quyết định 2 chiều (mức tin cậy của agent × risk của
        tool) — port từ `PolicyEngine.evaluate()` trong
        `legacy/agent_runtime/cosa_core/governance/policy_engine.py` theo
        ADR-014, thay cho lookup 1 chiều của `evaluate()`/`PermissionClass`
        ở trên. `evaluate()` (PermissionClass) VẪN GIỮ NGUYÊN, không xóa —
        `Executor`/`ApprovalGateStep` hiện tại vẫn dùng nó; cutover sang
        `evaluate_for_agent()` cho toàn bộ 17 tool binding thật trong
        `agentos/tools/clusters/*.py` cần gán `risk_level` thật cho từng
        tool (quyết định nghiệp vụ, không phải việc nên tự bịa hàng loạt) —
        đó là bước tích hợp riêng, chưa nằm trong lần port này. Dùng
        `PERMISSION_CLASS_RISK_MAPPING` bên dưới nếu cần 1 điểm khởi đầu
        suy ra từ đúng quyết định `DEFAULT_POLICY_TABLE` đã được duyệt.

        Không port phần "Agent Key Whitelist" và "chat_schema bypass" của
        bản gốc — `agentos.tools.registry.ToolSpec` chưa có khái niệm
        allowed_agent_keys/chat_schema, thêm vào đây sẽ là bịa field mới
        chưa ai yêu cầu.
        """
        if tool_risk_level == "critical":
            decision = PolicyDecision.REQUIRE_APPROVAL
        elif agent_permission_level == PermissionLevel.L0_READ:
            decision = PolicyDecision.ALLOW if tool_permission == "read_only" else PolicyDecision.DENY
        elif agent_permission_level == PermissionLevel.L1_SUGGEST:
            decision = PolicyDecision.ALLOW if tool_permission == "read_only" else PolicyDecision.REQUIRE_APPROVAL
        elif agent_permission_level == PermissionLevel.L2_DRAFT:
            if tool_permission == "read_only":
                decision = PolicyDecision.ALLOW
            elif tool_permission == "scoped_write" and tool_risk_level == "low":
                decision = PolicyDecision.ALLOW
            else:
                decision = PolicyDecision.REQUIRE_APPROVAL
        elif agent_permission_level == PermissionLevel.L3A_EXECUTE_WITH_APPROVAL:
            decision = PolicyDecision.ALLOW if tool_permission == "read_only" else PolicyDecision.REQUIRE_APPROVAL
        else:  # L3_EXECUTE
            if tool_risk_level in ("low", "medium") and tool_permission in ("read_only", "scoped_write", "admin_write"):
                decision = PolicyDecision.ALLOW
            else:
                decision = PolicyDecision.REQUIRE_APPROVAL

        if self._audit_sink is not None:
            self._audit_sink.record(
                event_type="policy.evaluated_for_agent",
                run_id=run_id,
                subject=f"{agent_permission_level.value}:{tool_risk_level}:{tool_permission}",
                decision=decision.value,
            )
        return decision


class PermissionLevel(str, enum.Enum):
    """Mức tin cậy được cấp cho 1 agent (port từ `PermissionLevel` trong
    `legacy/agent_runtime/cosa_core/governance/policy_engine.py`, ADR-014).
    Canonical governance vocabulary theo ADR-014 — `PermissionClass` ở trên
    là tag phân loại tool, không phải mức tin cậy agent.
    """

    L0_READ = "L0_READ"
    L1_SUGGEST = "L1_SUGGEST"
    L2_DRAFT = "L2_DRAFT"
    L3A_EXECUTE_WITH_APPROVAL = "L3A_EXECUTE_WITH_APPROVAL"
    L3_EXECUTE = "L3_EXECUTE"


class ExecutionMode(str, enum.Enum):
    """Chế độ thực thi runtime (§8.5, Phase 10a)."""

    INTERACTIVE = "interactive"
    APPROVED_WORKFLOW = "approved_workflow"
    AUTONOMOUS_SAFE = "autonomous_safe"


class DataScope(str, enum.Enum):
    """Phạm vi dữ liệu cho phép truy cập (§8.5, Phase 10a)."""

    WORKSPACE = "workspace"
    COMPANY = "company"
    READ_ONLY = "read_only"


class TenantPolicyDecision(str, enum.Enum):
    """Chính sách tenant đặc thù cấp công ty (§8.5, Phase 10a)."""

    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"


# Đường dẫn/tài nguyên core BẤT BIẾN nếu không có Admin/Founder grant tường
# minh — port nguyên trạng từ legacy (PROTECTED_CORE_RESOURCES).
PROTECTED_CORE_RESOURCES: frozenset[str] = frozenset(
    {"identity.md", "soul.md", "agents.md", "policies", "platform_prompt_templates", "system_assets"}
)


# permission_class -> (risk_level, tool_permission) — điểm khởi đầu suy ra
# TRỰC TIẾP từ đúng quyết định ALLOW/DENY/REQUIRE_APPROVAL đã có sẵn trong
# DEFAULT_POLICY_TABLE (không phải đánh giá rủi ro mới tự bịa): risk_level
# "critical" cho những permission_class trước đây DENY hoặc REQUIRE_APPROVAL
# ở mức cao nhất (ACCESS_SECRET, DEPLOY, FINANCIAL_ACTION — hành động khó
# đảo ngược/nhạy cảm nhất), "high" cho REQUIRE_APPROVAL còn lại có external
# side-effect, "medium"/"low" cho phần còn lại theo đúng tinh thần bảng cũ.
PERMISSION_CLASS_RISK_MAPPING: dict[PermissionClass, tuple[str, str]] = {
    PermissionClass.READ_LOCAL: ("low", "read_only"),
    PermissionClass.WRITE_WORKSPACE: ("low", "scoped_write"),
    PermissionClass.READ_NETWORK: ("low", "read_only"),
    PermissionClass.EXTERNAL_WRITE: ("high", "scoped_write"),
    PermissionClass.SEND_MESSAGE: ("high", "scoped_write"),
    PermissionClass.MODIFY_BUSINESS_DATA: ("medium", "scoped_write"),
    PermissionClass.DEPLOY: ("critical", "admin_write"),
    PermissionClass.EXECUTE_CODE: ("high", "admin_write"),
    PermissionClass.ACCESS_SECRET: ("critical", "admin_write"),
    PermissionClass.DELETE_DATA: ("high", "admin_write"),
    PermissionClass.FINANCIAL_ACTION: ("critical", "admin_write"),
}


def evaluate_execution_mode(
    mode: ExecutionMode,
    capability: str,
    *,
    risk_level: str = "low",
    target_resource: str | None = None,
) -> PolicyDecision:
    """Port nguyên trạng `PolicyEngine.evaluate_execution_mode()` từ
    `legacy/agent_runtime/cosa_core/governance/policy_engine.py` — đánh giá
    hành động theo Execution Mode + tính bất biến của core resource.
    """
    if target_resource:
        resource_lower = target_resource.lower()
        if any(protected in resource_lower for protected in PROTECTED_CORE_RESOURCES):
            if capability in ("write_file", "edit_file", "delete_file", "update_prompt"):
                return PolicyDecision.REQUIRE_APPROVAL

    mode_val = mode.value if isinstance(mode, ExecutionMode) else str(mode).lower()
    if mode_val == "autonomous_safe":
        if risk_level in ("high", "critical") or any(
            capability.startswith(prefix) for prefix in ("send_", "publish_", "payment_", "delete_", "mutate_")
        ):
            return PolicyDecision.DENY
        return PolicyDecision.ALLOW

    if mode_val == "approved_workflow":
        if risk_level == "critical":
            return PolicyDecision.REQUIRE_APPROVAL
        return PolicyDecision.ALLOW

    # INTERACTIVE (mặc định)
    if risk_level in ("high", "critical") or any(
        capability.startswith(prefix) for prefix in ("send_", "publish_", "payment_", "delete_")
    ):
        return PolicyDecision.REQUIRE_APPROVAL
    return PolicyDecision.ALLOW


def evaluate_access(
    *,
    role: str,
    agent_permission_level: PermissionLevel,
    tool_risk_level: ToolRiskLevel,
    tool_permission: ToolPermission,
    tenant_policy: TenantPolicyDecision | None = None,
    execution_mode: ExecutionMode | None = None,
    data_scope: DataScope | None = None,
    approval_policy: str | None = None,
) -> PolicyDecision:
    """Full 6-Dimension Access Decision Function (§8.5, Phase 10a):
    Decision = RBAC/Entitlement ∩ TenantPolicy ∩ AgentPermissionLevel ∩ ToolRisk ∩ ExecutionMode ∩ DataScope

    Intersection principle:
    - If ANY dimension returns DENY -> final decision is DENY.
    - Else if ANY dimension returns REQUIRE_APPROVAL -> final decision is REQUIRE_APPROVAL.
    - Only returns ALLOW when ALL dimensions evaluate to ALLOW.
    """
    if isinstance(tool_risk_level, str):
        tool_risk_level = ToolRiskLevel(tool_risk_level.lower())
    if isinstance(tool_permission, str):
        tool_permission = ToolPermission(tool_permission.lower())
    if isinstance(agent_permission_level, str):
        agent_permission_level = PermissionLevel(agent_permission_level)
    if isinstance(execution_mode, str):
        try:
            execution_mode = ExecutionMode(execution_mode.lower())
        except ValueError:
            execution_mode = None
    if isinstance(data_scope, str):
        try:
            data_scope = DataScope(data_scope.lower())
        except ValueError:
            data_scope = None
    if isinstance(tenant_policy, str):
        try:
            tenant_policy = TenantPolicyDecision(tenant_policy.upper())
        except ValueError:
            tenant_policy = None

    decisions: list[PolicyDecision] = []

    # 1. RBAC & Agent Permission Level & Tool Risk & Tool Permission
    norm_role = role.lower().strip()
    if tool_permission == ToolPermission.READ_ONLY:
        if norm_role in ("founder", "co-founder", "user", "auditor", "admin", "member"):
            if approval_policy == "always":
                decisions.append(PolicyDecision.REQUIRE_APPROVAL)
            else:
                decisions.append(PolicyDecision.ALLOW)
        else:
            decisions.append(PolicyDecision.DENY)
    elif norm_role == "auditor":
        decisions.append(PolicyDecision.DENY)
    elif norm_role not in ("founder", "co-founder", "user", "admin", "member"):
        decisions.append(PolicyDecision.DENY)
    elif approval_policy == "always":
        decisions.append(PolicyDecision.REQUIRE_APPROVAL)
    elif approval_policy == "never":
        decisions.append(PolicyDecision.ALLOW)
    elif norm_role in ("founder", "admin"):
        if tool_risk_level in (ToolRiskLevel.LOW, ToolRiskLevel.MEDIUM):
            decisions.append(PolicyDecision.ALLOW)
        elif agent_permission_level == PermissionLevel.L3_EXECUTE:
            decisions.append(PolicyDecision.ALLOW)
        else:
            decisions.append(PolicyDecision.REQUIRE_APPROVAL)
    elif norm_role in ("co-founder", "user", "member"):
        if tool_risk_level in (ToolRiskLevel.LOW, ToolRiskLevel.MEDIUM):
            if agent_permission_level in (PermissionLevel.L2_DRAFT, PermissionLevel.L3_EXECUTE):
                decisions.append(PolicyDecision.ALLOW)
            else:
                decisions.append(PolicyDecision.REQUIRE_APPROVAL)
        else:
            decisions.append(PolicyDecision.REQUIRE_APPROVAL)
    else:
        decisions.append(PolicyDecision.DENY)

    # 2. Tenant Policy
    if tenant_policy is not None:
        if tenant_policy == TenantPolicyDecision.DENY:
            decisions.append(PolicyDecision.DENY)
        elif tenant_policy == TenantPolicyDecision.REQUIRE_APPROVAL:
            decisions.append(PolicyDecision.REQUIRE_APPROVAL)
        else:
            decisions.append(PolicyDecision.ALLOW)

    # 3. Data Scope
    if data_scope == DataScope.READ_ONLY:
        if tool_permission != ToolPermission.READ_ONLY:
            # DataScope.READ_ONLY overrides any write tool to DENY
            decisions.append(PolicyDecision.DENY)
        else:
            decisions.append(PolicyDecision.ALLOW)

    # 4. Execution Mode
    if execution_mode == ExecutionMode.AUTONOMOUS_SAFE:
        # Autonomous mode without human in the loop only permits LOW and MEDIUM risks.
        # High and Critical risks must be DENIED (no human is present to approve).
        if tool_risk_level in (ToolRiskLevel.HIGH, ToolRiskLevel.CRITICAL):
            decisions.append(PolicyDecision.DENY)
        else:
            decisions.append(PolicyDecision.ALLOW)
    elif execution_mode == ExecutionMode.INTERACTIVE:
        # In interactive mode, safety requires approval for high/critical writes for non-full-autonomy principals
        if tool_risk_level in (ToolRiskLevel.HIGH, ToolRiskLevel.CRITICAL) and tool_permission != ToolPermission.READ_ONLY:
            if norm_role in ("founder", "admin") and agent_permission_level == PermissionLevel.L3_EXECUTE:
                # Decision note: Founder with L3_EXECUTE maintains full autonomy ceiling in interactive mode
                decisions.append(PolicyDecision.ALLOW)
            elif approval_policy == "never":
                decisions.append(PolicyDecision.ALLOW)
            else:
                decisions.append(PolicyDecision.REQUIRE_APPROVAL)
        else:
            decisions.append(PolicyDecision.ALLOW)
    elif execution_mode == ExecutionMode.APPROVED_WORKFLOW:
        decisions.append(PolicyDecision.ALLOW)

    # Combine via Intersection:
    if PolicyDecision.DENY in decisions:
        return PolicyDecision.DENY
    if PolicyDecision.REQUIRE_APPROVAL in decisions:
        return PolicyDecision.REQUIRE_APPROVAL
    return PolicyDecision.ALLOW


