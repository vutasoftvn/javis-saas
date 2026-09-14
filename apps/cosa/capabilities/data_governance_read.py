from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient

logger = logging.getLogger("cosa.capabilities.data_governance_read")

__all__ = ["DATA_GOVERNANCE_READ_SPEC", "create_data_governance_read_handler"]

DATA_GOVERNANCE_READ_SPEC = CapabilitySpec(
    id="data.governance.read",
    description=(
        "Đọc snapshot Data Governance Dossier mới nhất của một Project "
        "(Read-only, chỉ metadata catalog đã phân loại — assetId/"
        "classification/qualityStatus/sourceRefs — không có giá trị/field "
        "sample thật, embedding vector, raw file URI hay API credential; "
        "không có quyền tạo/append)."
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
            "assets": {"type": "array"},
            "sourceRefs": {"type": "array"},
            "status": {"type": "string"},
        },
    },
)


def create_data_governance_read_handler(
    company_client: CompanyServiceClient,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    async def handle(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        workspace_id = _resolve_workspace_id(ctx)
        project_id = _resolve_project_id(args, ctx)

        headers = {"X-Workspace-Id": str(workspace_id)}

        snapshot = await company_client.get(
            f"/operations/projects/{project_id}/data-governance-dossier",
            headers=headers,
        )

        if not isinstance(snapshot, dict):
            snapshot = {}

        # Chỉ trả về đúng các field snapshot đã redact/phân loại tại nguồn
        # (Task 1) — không thêm bất kỳ raw value/embedding/raw-file-URI/
        # credential surface mới nào.
        return {
            "dossierId": snapshot.get("dossierId"),
            "revision": snapshot.get("revision"),
            "assets": snapshot.get("assets", []),
            "sourceRefs": snapshot.get("sourceRefs", []),
            "status": snapshot.get("status"),
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
    context_project_id = (
        ctx.get("project_id") if isinstance(ctx, dict) else getattr(ctx, "project_id", None)
    )
    context_project_id = str(context_project_id) if context_project_id else None

    requested_project_id = args.get("project_id")
    requested_project_id = str(requested_project_id) if requested_project_id else None

    if context_project_id and requested_project_id and requested_project_id != context_project_id:
        raise ValueError(
            "data.governance.read: project_id trong args không khớp scope của run "
            f"(ctx.project_id={context_project_id!r}, args.project_id={requested_project_id!r})"
        )

    project_id = context_project_id or requested_project_id
    if not project_id:
        raise ValueError("data.governance.read: thiếu project_id")
    return project_id


def _resolve_workspace_id(ctx: Any) -> str:
    """workspace_id LUÔN lấy từ ctx (scope thật của run) — không phải input_schema
    khai báo, args không có quyền ghi đè trường này dù thế nào.
    """
    wid = ctx.get("workspace_id") if isinstance(ctx, dict) else getattr(ctx, "workspace_id", None)
    if not wid:
        raise ValueError("data.governance.read: thiếu workspace_id trong ctx")
    return str(wid)
