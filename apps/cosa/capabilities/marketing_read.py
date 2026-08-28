from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine, Optional

from agent_core.contracts.capability import CapabilitySpec
from agent_core.governance.contracts import ApprovalPolicy, CapabilityRisk
from apps.cosa.capabilities.client import CompanyServiceClient

logger = logging.getLogger("cosa.capabilities.marketing_read")

__all__ = [
    "MARKETING_CONTEXT_READ_SPEC",
    "create_marketing_context_read_handler",
]

MARKETING_CONTEXT_READ_SPEC = CapabilitySpec(
    id="commercial.marketing_context.read",
    description="Đọc dữ liệu marketing context (sản phẩm, ICP, brand voice, competitors, evidence) của workspace.",
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    idempotency_semantics="payload_deterministic",
    input_schema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "ID của workspace cần truy vấn marketing context",
            }
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "context": {"type": "object", "description": "Dữ liệu canonical marketing context"},
            "status": {"type": "string", "description": "Trạng thái (draft, in_review, approved, empty)"},
            "missing_evidence": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Danh sách các khía cạnh còn thiếu bằng chứng xác thực",
            },
        },
    },
)


def create_marketing_context_read_handler(
    company_client: CompanyServiceClient,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    """Tạo capability handler đọc marketing context an toàn từ company service."""

    async def handle_marketing_context_read(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        # 1. Resolve workspace_id từ context hoặc args
        workspace_id: Optional[str] = None
        if isinstance(ctx, dict):
            workspace_id = ctx.get("workspace_id")
        elif hasattr(ctx, "workspace_id"):
            workspace_id = getattr(ctx, "workspace_id")

        if not workspace_id and "workspace_id" in args:
            workspace_id = str(args["workspace_id"])

        if not workspace_id:
            raise ValueError("Không thể thực hiện commercial.marketing_context.read: thiếu workspace_id")

        headers = {"X-Workspace-Id": str(workspace_id)}

        try:
            res = await company_client.get(
                f"/commercial/marketing-context?workspace_id={workspace_id}",
                headers=headers,
            )
        except Exception as e:
            logger.warning("Lỗi truy vấn marketing context cho workspace %s: %s", workspace_id, e)
            res = None

        # 2. Xử lý trường hợp context chưa có dữ liệu hoặc rỗng
        if not res or not isinstance(res, dict) or not res.get("id"):
            return {
                "workspace_id": workspace_id,
                "context": None,
                "status": "empty",
                "missing_evidence": [
                    "icp_segments",
                    "positioning_statement",
                    "brand_voice",
                    "key_differentiators",
                    "empirical_evidence",
                ],
                "message": "Marketing context chưa được thiết lập cho workspace này. Cần thu thập và xác thực bằng chứng thực nghiệm trước khi công bố.",
            }

        # 3. Trả về context đã cấu trúc đầy đủ
        return {
            "workspace_id": workspace_id,
            "context": res,
            "revision": res.get("revision", 1),
            "status": res.get("status", "draft"),
            "missing_evidence": [],
        }

    return handle_marketing_context_read
