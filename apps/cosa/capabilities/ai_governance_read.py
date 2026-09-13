from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient

logger = logging.getLogger("cosa.capabilities.ai_governance_read")

__all__ = ["AI_GOVERNANCE_READ_SPEC", "create_ai_governance_read_handler"]

AI_GOVERNANCE_READ_SPEC = CapabilitySpec(
    id="ai.governance.read",
    description=(
        "Đọc snapshot AI Governance Dossier mới nhất của một Project "
        "(Read-only, chỉ tham chiếu policy/evaluator đã ký (id/version/hash), "
        "risk signal đã phân loại (category/severity) và source ref đã redact "
        "— KHÔNG có prompt/output transcript thật, API key/provider credential, "
        "raw user message hay model output; không có quyền tạo/append)."
    ),
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    idempotency_semantics="payload_deterministic",
    input_schema={
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "project_id": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "dossierId": {"type": "string"},
            "revision": {"type": "integer"},
            "status": {"type": "string"},
            "snapshotRef": {"type": "string"},
            "policy": {"type": "array"},
            "evaluators": {"type": "array"},
            "observedAt": {"type": "string"},
            "riskSignals": {"type": "array"},
            "sourceRefs": {"type": "array"},
        },
    },
)


def create_ai_governance_read_handler(
    company_client: CompanyServiceClient,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    async def handle(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        workspace_id = _resolve_workspace_id(ctx)
        project_id = _resolve_project_id(args, ctx)

        headers = {"X-Workspace-Id": str(workspace_id)}

        snapshot = await company_client.get(
            f"/operations/projects/{project_id}/ai-governance-dossier",
            headers=headers,
        )

        if not isinstance(snapshot, dict):
            snapshot = {}

        # Chỉ trả về đúng các field snapshot đã redact/phân loại tại nguồn
        # (Task 2, `readAiGovernanceSnapshot`) — không thêm bất kỳ raw
        # signature/prompt/output/credential surface mới nào.
        return {
            "dossierId": snapshot.get("dossierId"),
            "revision": snapshot.get("revision"),
            "status": snapshot.get("status"),
            "snapshotRef": snapshot.get("snapshotRef"),
            "policy": snapshot.get("policy", []),
            "evaluators": snapshot.get("evaluators", []),
            "observedAt": snapshot.get("observedAt"),
            "riskSignals": snapshot.get("riskSignals", []),
            "sourceRefs": snapshot.get("sourceRefs", []),
        }

    return handle


def _resolve_project_id(args: dict[str, Any], ctx: Any) -> str:
    """Xác định project_id cho request — ctx (scope thật của run) LUÔN thắng.

    Trong pipeline invocation thật (`packages/agent/capabilities/gateway.py`,
    `apps/cosa/worker/copilot_run.py`), `ctx` LUÔN LÀ một `dict` thuần —
    không bao giờ là object. Vì vậy dùng `ctx.get(...)`/`isinstance` check
    (giống `_resolve_workspace_id`) thay vì `getattr` (dead code với dict).

    `project_id` là input bắt buộc theo input_schema (một số caller nội bộ
    vẫn truyền nó tường minh), nhưng model/agent không được phép dùng nó để
    đọc dossier của Project khác ngoài scope run đang chạy. Nếu
    args["project_id"] khác ctx["project_id"], coi đây là request sai lệch
    scope và từ chối thẳng thay vì âm thầm override — không được để lộ dữ
    liệu Project khác.
    """
    context_project_id = ctx.get("project_id") if isinstance(ctx, dict) else getattr(ctx, "project_id", None)
    context_project_id = str(context_project_id) if context_project_id else None

    requested_project_id = args.get("project_id")
    requested_project_id = str(requested_project_id) if requested_project_id else None

    if context_project_id and requested_project_id and requested_project_id != context_project_id:
        raise ValueError(
            "ai.governance.read: project_id trong args không khớp scope của run "
            f"(ctx.project_id={context_project_id!r}, args.project_id={requested_project_id!r})"
        )

    project_id = context_project_id or requested_project_id
    if not project_id:
        raise ValueError("ai.governance.read: thiếu project_id")
    return project_id


def _resolve_workspace_id(ctx: Any) -> str:
    """workspace_id LUÔN lấy từ ctx (scope thật của run) — không phải input_schema
    khai báo, args không có quyền ghi đè trường này dù thế nào.
    """
    wid = ctx.get("workspace_id") if isinstance(ctx, dict) else getattr(ctx, "workspace_id", None)
    if not wid:
        raise ValueError("ai.governance.read: thiếu workspace_id trong ctx")
    return str(wid)
