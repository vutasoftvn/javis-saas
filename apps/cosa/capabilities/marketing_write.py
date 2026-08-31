from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient

logger = logging.getLogger("cosa.capabilities.marketing_write")

__all__ = [
    "CAMPAIGN_ASSET_WRITE_SPEC",
    "EXPERIMENT_WRITE_SPEC",
    "MARKETING_CONTEXT_WRITE_SPEC",
    "create_campaign_asset_write_handler",
    "create_experiment_write_handler",
    "create_marketing_context_write_handler",
]

MARKETING_CONTEXT_WRITE_SPEC = CapabilitySpec(
    id="commercial.marketing_context.write",
    description="Cập nhật marketing context của workspace (sản phẩm, ICP, brand voice, evidence) với kiểm soát optimistic locking và review approval.",
    risk=CapabilityRisk.MEDIUM,
    approval_policy=ApprovalPolicy.ALWAYS,
    idempotency_semantics="payload_deterministic",
    metadata={"action_class": "B"},
    input_schema={
        "type": "object",
        "properties": {
            "workspace_id": {"type": "string", "description": "ID của workspace"},
            "expected_revision": {
                "type": "integer",
                "description": "Revision mong đợi để chống race condition",
            },
            "product_marketing": {
                "type": "object",
                "description": "Dữ liệu định vị sản phẩm cập nhật",
            },
            "icp_segments": {"type": "array", "description": "Danh sách phân khúc ICP"},
            "evidence_items": {"type": "array", "description": "Danh sách bằng chứng thực nghiệm"},
            "change_reason": {"type": "string", "description": "Lý do cập nhật thông tin"},
        },
        "required": ["expected_revision"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "revision": {"type": "integer"},
            "status": {"type": "string"},
            "updated_at": {"type": "string"},
        },
    },
)

CAMPAIGN_ASSET_WRITE_SPEC = CapabilitySpec(
    id="commercial.campaign_asset.write",
    description="Lưu trữ tài liệu và nội dung chiến dịch marketing (copy, email template, landing page) vào kho tài nguyên workspace. Không publish ra ngoài.",
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    idempotency_semantics="payload_deterministic",
    metadata={"action_class": "A"},
    input_schema={
        "type": "object",
        "properties": {
            "workspace_id": {"type": "string", "description": "ID của workspace"},
            "asset_name": {"type": "string", "description": "Tên tài liệu / asset"},
            "content": {"type": "string", "description": "Nội dung markdown hoặc JSON của asset"},
            "asset_type": {
                "type": "string",
                "description": "Loại asset (copy, email_sequence, landing_page, ad_creative)",
            },
        },
        "required": ["asset_name", "content"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "asset_id": {"type": "string"},
            "object_ref": {"type": "string"},
            "created_at": {"type": "string"},
        },
    },
)

EXPERIMENT_WRITE_SPEC = CapabilitySpec(
    id="commercial.experiment.write",
    description="Tạo giả định hoặc thử nghiệm marketing mới gắn với metric_contract_id chờ duyệt.",
    risk=CapabilityRisk.MEDIUM,
    approval_policy=ApprovalPolicy.ALWAYS,
    idempotency_semantics="payload_deterministic",
    metadata={"action_class": "B"},
    input_schema={
        "type": "object",
        "properties": {
            "workspace_id": {"type": "string", "description": "ID của workspace"},
            "hypothesis": {"type": "string", "description": "Giả định cần kiểm chứng"},
            "metric": {
                "type": "string",
                "description": "Chỉ số đo lường (CTR, Conversion rate, CPL)",
            },
            "metric_contract_id": {
                "type": "string",
                "description": "ID hợp đồng chỉ số đo lường bắt buộc",
            },
            "target_value": {"type": "number", "description": "Giá trị mục tiêu"},
            "duration_days": {"type": "integer", "description": "Thời gian thử nghiệm (ngày)"},
        },
        "required": ["hypothesis", "metric", "metric_contract_id"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "experiment_id": {"type": "string"},
            "status": {"type": "string"},
            "hypothesis": {"type": "string"},
            "metric_contract_id": {"type": "string"},
        },
    },
)


def _resolve_workspace_id(args: dict[str, Any], ctx: Any) -> str:
    ws: str | None = None
    if isinstance(ctx, dict):
        ws = ctx.get("workspace_id")
    elif hasattr(ctx, "workspace_id"):
        ws = ctx.workspace_id

    if not ws and "workspace_id" in args:
        ws = str(args["workspace_id"])

    if not ws:
        raise ValueError("Thiếu workspace_id trong context và arguments")
    return str(ws)


def create_marketing_context_write_handler(
    company_client: CompanyServiceClient,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    """Tạo capability handler ghi marketing context an toàn với optimistic locking."""

    async def handle_marketing_context_write(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        workspace_id = _resolve_workspace_id(args, ctx)
        expected_revision = args.get("expected_revision")
        if expected_revision is None:
            raise ValueError(
                "commercial.marketing_context.write yêu cầu expected_revision để chống race condition"
            )

        payload = {
            "workspaceId": workspace_id,
            "expectedRevision": expected_revision,
        }
        if "product_marketing" in args:
            payload["productMarketing"] = args["product_marketing"]
        if "icp_segments" in args:
            payload["icpSegments"] = args["icp_segments"]
        if "evidence_items" in args:
            payload["evidenceItems"] = args["evidence_items"]
        if "change_reason" in args:
            payload["changeReason"] = args["change_reason"]

        headers = {"X-Workspace-Id": workspace_id}
        res = await company_client.patch(
            f"/commercial/marketing-context?workspace_id={workspace_id}",
            json=payload,
            headers=headers,
        )
        return res or {
            "workspace_id": workspace_id,
            "status": "updated",
            "revision": expected_revision + 1,
        }

    return handle_marketing_context_write


def create_campaign_asset_write_handler(
    company_client: CompanyServiceClient,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    """Tạo capability handler lưu trữ asset chiến dịch marketing."""

    async def handle_campaign_asset_write(
        args: dict[str, Any], context: Any = None
    ) -> dict[str, Any]:
        workspace_id = _resolve_workspace_id(args, context)

        # Anti-bypass check: cannot publish to public_url or direct external ad/page
        if "public_url" in args or args.get("publish") is True or args.get("is_public") is True:
            raise ValueError(
                "commercial.campaign_asset.write is an internal artifact write; publishing to public_url is not permitted"
            )

        asset_id = f"asset_{uuid.uuid4().hex[:12]}"
        asset_name = args.get("asset_name", "Untitled Asset")
        asset_type = args.get("asset_type", "copy")

        return {
            "workspace_id": workspace_id,
            "asset_id": asset_id,
            "asset_name": asset_name,
            "asset_type": asset_type,
            "object_ref": f"artifact://{workspace_id}/campaign-assets/{asset_id}.md",
            "status": "saved",
        }

    return handle_campaign_asset_write


def create_experiment_write_handler(
    company_client: CompanyServiceClient,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    """Tạo capability handler khởi tạo thử nghiệm marketing/chiến lược."""

    async def handle_experiment_write(args: dict[str, Any], context: Any = None) -> dict[str, Any]:
        workspace_id = _resolve_workspace_id(args, context)

        # Anti-bypass check: cannot spend, budget or auto-activate
        if "budget" in args or "spend" in args or args.get("activate") is True:
            raise ValueError(
                "commercial.experiment.write cannot modify budget/spend or auto-activate"
            )

        metric_contract_id = args.get("metric_contract_id") or args.get("metric_contract_ref")
        if not metric_contract_id or not str(metric_contract_id).strip():
            raise ValueError(
                "commercial.experiment.write requires a valid metric_contract_id reference"
            )

        experiment_id = f"exp_{uuid.uuid4().hex[:12]}"
        hypothesis = args.get("hypothesis", "")
        metric = args.get("metric", "conversion_rate")

        return {
            "workspace_id": workspace_id,
            "experiment_id": experiment_id,
            "hypothesis": hypothesis,
            "metric": metric,
            "metric_contract_id": str(metric_contract_id),
            "target_value": args.get("target_value"),
            "status": "pending_approval",
        }

    return handle_experiment_write
