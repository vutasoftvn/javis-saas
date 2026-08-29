from __future__ import annotations

from typing import Any

__all__ = ["verify_ambient_governance"]


def verify_ambient_governance(context: Any) -> tuple[bool, str]:
    """Kiểm tra tính hợp lệ của môi trường quản trị tức thời (ambient governance).

    Được gọi ở cả lần execute đầu tiên và khi resume sau approval,
    ngay trước khi thực hiện side-effect thực sự.

    Kiểm tra:
    1. Tenant status: không bị suspended hoặc disabled.
    2. Principal status: không bị revoked hoặc disabled.
    3. Emergency lock / Kill switch: không kích hoạt.
    4. Human takeover / Thread takeover: không bật.
    """
    if context is None:
        return True, ""

    if hasattr(context, "metadata") and isinstance(context.metadata, dict):
        ctx_dict = dict(context.metadata)
        if hasattr(context, "policy_snapshot") and context.policy_snapshot:
            ctx_dict.update(context.policy_snapshot)
    elif isinstance(context, dict):
        ctx_dict = context
    else:
        ctx_dict = {}

    tenant_status = ctx_dict.get("tenant_status", "active")
    if tenant_status in {"suspended", "disabled"}:
        return False, f"Tenant is currently {tenant_status}"

    principal_status = ctx_dict.get("principal_status", "active")
    if principal_status in {"revoked", "disabled"}:
        return False, f"Principal is currently {principal_status}"

    if ctx_dict.get("emergency_lock", False) or ctx_dict.get("kill_switch", False):
        return False, "Emergency lock / kill switch is active"

    if ctx_dict.get("human_takeover", False) or ctx_dict.get("takeover", False) or ctx_dict.get("thread_takeover", False):
        return False, "Human takeover is active"

    return True, ""
