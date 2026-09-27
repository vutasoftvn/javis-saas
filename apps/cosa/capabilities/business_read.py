"""`business.read`: MỘT tool đọc cho mọi domain business (spec 2026-09-27-chat-business-actions
§4.2), thay vì nhồi ~15 tool đọc vào chat (model yếu bị quá tải schema tool).

Mỗi domain dispatch tới capability đọc đã có; quyền truy cập vẫn do handler đó và AGENT_CAP
riêng của nó ở company quyết định — không có quyền mới. Vì company kiểm capability trên
delegation token, token của run có `business.read` phải mang thêm đúng các capability đích
(`delegated_capability_ids`, dùng ở ComplianceResolver) — không hơn.

Scope (`workspace_id`, `project_id`) lấy từ run, không từ model; kết quả được rút gọn để
không tràn ngữ cảnh model.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

__all__ = [
    "BUSINESS_READ_SPEC",
    "DOMAIN_TO_CAPABILITY",
    "create_business_read_handler",
    "delegated_capability_ids",
]

# domain -> capability đọc sẵn có (T0, có AGENT_CAP ở company). `customer` (Customer 360)
# không có ở đây vì cần contact_id cụ thể — không phải truy vấn tổng quan theo domain.
DOMAIN_TO_CAPABILITY: dict[str, str] = {
    "goals": "startup_os.goal.tree_read",
    "okr": "okr.objective.list",
    "finance": "finance.transaction.read",
    "crm": "project.crm.read",
    "legal": "legal.issue.read",
    "people": "people.risk.read",
    "product": "product.decision.read",
    "security": "security.posture.read",
    "data": "data.governance.read",
    "ai_governance": "ai.governance.read",
    "marketing": "commercial.marketing_context.read",
    "venture": "venture.profile.read",
    "evidence": "strategy.evidence.list",
    "metrics": "analytics.metric_contract.get",
}

_LIST_LIMIT = 20

BUSINESS_READ_SPEC = CapabilitySpec(
    id="business.read",
    description=(
        "Read business data of the current workspace/project by domain: "
        + ", ".join(sorted(DOMAIN_TO_CAPABILITY))
        + ". Call it before answering questions about goals, OKRs, finance, CRM, legal, "
        "people, product, security, data, marketing or the venture profile. Scope is taken "
        "from the current session — do not pass ids."
    ),
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    input_schema={
        "type": "object",
        "required": ["domain"],
        "properties": {"domain": {"type": "string", "enum": sorted(DOMAIN_TO_CAPABILITY)}},
    },
    output_schema={"type": "object", "properties": {"domain": {"type": "string"}, "data": {}}},
)

Dispatch = Callable[[str, dict[str, Any], Any], Awaitable[Any]]


def delegated_capability_ids(capability_refs: Iterable[str]) -> list[str]:
    """Capability đích mà delegation token phải mang thêm khi spec có `business.read`."""
    if BUSINESS_READ_SPEC.id not in set(capability_refs):
        return []
    return sorted(set(DOMAIN_TO_CAPABILITY.values()))


def _scope_value(context: Any, key: str) -> Any:
    if isinstance(context, dict):
        return context.get(key)
    value = getattr(context, key, None)
    if value in (None, ""):
        metadata = getattr(context, "metadata", None)
        if isinstance(metadata, dict):
            value = metadata.get(key)
    return value


def _compact(data: Any, limit: int = _LIST_LIMIT) -> Any:
    """Cắt danh sách dài còn `limit` phần tử (kèm tổng số) ở mọi mức lồng nhau."""
    if isinstance(data, list):
        items = [_compact(item, limit) for item in data[:limit]]
        if len(data) > limit:
            return {"items": items, "truncated": True, "total": len(data)}
        return items
    if isinstance(data, dict):
        return {key: _compact(value, limit) for key, value in data.items()}
    return data


def create_business_read_handler(dispatch: Dispatch):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        domain = str(payload.get("domain") or "")
        cap_id = DOMAIN_TO_CAPABILITY.get(domain)
        if cap_id is None:
            raise ValueError(
                f"business.read: domain không hợp lệ {domain!r}; hợp lệ: {sorted(DOMAIN_TO_CAPABILITY)}"
            )
        scoped = {
            key: value
            for key in ("workspace_id", "project_id")
            if (value := _scope_value(context, key)) not in (None, "")
        }
        data = await dispatch(cap_id, scoped, context)
        return {"domain": domain, "data": _compact(data)}

    return handler
