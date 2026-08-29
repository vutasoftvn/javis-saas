from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

from apps.cosa.capabilities._advisory_envelope import wrap_advisory
from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "FINANCE_ACCOUNTING_DOCUMENT_CONFIRM_SPEC",
    "FINANCE_ACCOUNTING_DOCUMENT_CREATE_DRAFT_SPEC",
    "FINANCE_TRANSACTION_CLASSIFY_PROPOSE_SPEC",
    "FINANCE_TRANSACTION_RECORD_SPEC",
    "create_finance_accounting_document_confirm_handler",
    "create_finance_accounting_document_create_draft_handler",
    "create_finance_transaction_classify_propose_handler",
    "create_finance_transaction_record_handler",
]

FINANCE_TRANSACTION_RECORD_SPEC = CapabilitySpec(
    id="finance.transaction.record",
    description="Ghi nhận giao dịch tài chính (thu/chi) vào sổ cái của workspace.",
    risk=CapabilityRisk.MEDIUM,
    input_schema={
        "type": "object",
        "required": ["amount", "direction", "description"],
        "properties": {
            "amount": {"type": "number", "minimum": 0},
            "direction": {"type": "string", "enum": ["IN", "OUT", "inbound", "outbound"]},
            "description": {"type": "string", "minLength": 1},
            "category": {"type": "string"},
            "occurred_at": {"type": "string", "format": "date-time"},
            "workspace_id": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "workspace_id": {"type": "string"},
            "amount": {"type": "string"},
            "direction": {"type": "string"},
            "approval_status": {"type": "string"},
        },
    },
)

FINANCE_TRANSACTION_CLASSIFY_PROPOSE_SPEC = CapabilitySpec(
    id="finance.transaction.classify_propose",
    description="Đề xuất đối soát hoặc phân loại giao dịch ngân hàng khớp với chứng từ kế toán.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["bank_transaction_id", "accounting_document_id", "confidence"],
        "properties": {
            "workspace_id": {"type": "integer"},
            "bank_transaction_id": {"type": "string"},
            "accounting_document_id": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "proposal": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)

FINANCE_ACCOUNTING_DOCUMENT_CREATE_DRAFT_SPEC = CapabilitySpec(
    id="finance.accounting_document.create_draft",
    description="Tạo chứng từ kế toán nháp (phiếu thu/chi/hóa đơn) theo chuẩn TT58 cho doanh nghiệp duyệt.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["document_type", "number", "document_date", "amount", "description"],
        "properties": {
            "workspace_id": {"type": "integer"},
            "document_type": {
                "type": "string",
                "enum": ["RECEIPT", "PAYMENT", "INVOICE", "JOURNAL"],
            },
            "number": {"type": "string"},
            "document_date": {"type": "string"},
            "amount": {"type": "number"},
            "description": {"type": "string"},
            "line_items": {"type": "array"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "document": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)

FINANCE_ACCOUNTING_DOCUMENT_CONFIRM_SPEC = CapabilitySpec(
    id="finance.accounting_document.confirm",
    description="Xác nhận chứng từ kế toán chính thức vào sổ sách (bắt buộc duyệt qua Approval Policy).",
    risk=CapabilityRisk.HIGH,
    approval_policy=ApprovalPolicy.ALWAYS,
    input_schema={
        "type": "object",
        "required": ["document_id"],
        "properties": {
            "workspace_id": {"type": "integer"},
            "document_id": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "document": {"type": "object"},
        },
    },
)


def create_finance_transaction_record_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handle_transaction(payload: dict[str, Any], ctx: Any) -> dict[str, Any]:
        raw_ws_id = payload.get("workspace_id") or (
            ctx.get("workspace_id") if isinstance(ctx, dict) else getattr(ctx, "workspace_id", None)
        )
        if not raw_ws_id:
            return {"success": False, "error": "workspace_id is required"}
        workspace_id = str(raw_ws_id)

        direction_raw = str(payload.get("direction", "")).upper()
        if direction_raw in ("INBOUND", "IN"):
            direction = "IN"
        elif direction_raw in ("OUTBOUND", "OUT"):
            direction = "OUT"
        else:
            direction = "OUT"

        occurred_at = payload.get("occurred_at") or datetime.now(UTC).isoformat()

        body: dict[str, Any] = {
            "workspaceId": workspace_id,
            "amount": str(payload["amount"]),
            "direction": direction,
            "description": payload["description"],
            "transactionDate": occurred_at,
        }
        if payload.get("category"):
            body["category"] = payload["category"]

        res = await svc_client.post("/finance-legal/transactions", json=body)
        return res

    return handle_transaction


def create_finance_transaction_classify_propose_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = payload.get("workspace_id") or (
            context.get("workspace_id")
            if isinstance(context, dict)
            else getattr(context, "workspace_id", None)
        )
        headers = {}
        if ws_id:
            headers["X-Workspace-Id"] = str(ws_id)

        body = {
            "bankTransactionId": payload["bank_transaction_id"],
            "accountingDocumentId": payload["accounting_document_id"],
            "confidence": payload["confidence"],
        }
        res = await client.post("/finance/reconciliation-proposals", json=body, headers=headers)

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="proposal",
            content="Đã lập đề xuất đối soát giao dịch ngân hàng với chứng từ kế toán tương ứng.",
            sources=[],
            confidence=payload["confidence"],
            next_actions=[
                "Người phụ trách tài chính đối chiếu và bấm Chấp nhận trên màn hình Giao dịch"
            ],
        )

        return {"proposal": res, "advisory": advisory}

    return handler


def create_finance_accounting_document_create_draft_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = payload.get("workspace_id") or (
            context.get("workspace_id")
            if isinstance(context, dict)
            else getattr(context, "workspace_id", None)
        )
        headers = {}
        if ws_id:
            headers["X-Workspace-Id"] = str(ws_id)

        body = {
            "documentType": payload["document_type"],
            "number": payload["number"],
            "documentDate": payload["document_date"],
            "amount": payload["amount"],
            "description": payload["description"],
            "lineItems": payload.get("line_items", []),
        }
        doc = await client.post("/finance/accounting-documents", json=body, headers=headers)

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="proposal",
            content=f"Đã lập chứng từ nháp số {payload['number']} ({payload['document_type']}). Cần Founder xác nhận để vào sổ kế toán.",
            sources=[{"number": "58/2026/TT-BTC", "version": "2026"}],
            confidence=0.95,
            next_actions=[
                "Xem chi tiết chứng từ và bấm xác nhận để ghi nhận doanh thu/chi phí chính thức"
            ],
        )

        return {"document": doc, "advisory": advisory}

    return handler


def create_finance_accounting_document_confirm_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = payload.get("workspace_id") or (
            context.get("workspace_id")
            if isinstance(context, dict)
            else getattr(context, "workspace_id", None)
        )
        headers = {}
        if ws_id:
            headers["X-Workspace-Id"] = str(ws_id)

        doc_id = payload["document_id"]
        doc = await client.post(f"/finance/accounting-documents/{doc_id}/confirm", headers=headers)
        return {"document": doc}

    return handler
