from __future__ import annotations

from typing import Any, Optional
from agent_core.contracts.capability import CapabilitySpec
from agent_core.governance.contracts import CapabilityRisk
from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "FINANCE_PAYOUT_EXECUTE_SPEC",
    "FINANCE_TRANSACTION_RECORD_SPEC",
    "create_finance_payout_execute_handler",
    "create_finance_transaction_record_handler",
]

FINANCE_PAYOUT_EXECUTE_SPEC = CapabilitySpec(
    id="finance.payout.execute",
    name="Execute Finance Payout",
    description="Thực hiện giải ngân thanh toán tài chính qua services/company/finance-legal (Yêu cầu Human Approval).",
    risk=CapabilityRisk.HIGH,
    input_schema={
        "type": "object",
        "required": ["amount", "vendor", "currency", "idempotency_key"],
        "properties": {
            "amount": {"type": "number"},
            "vendor": {"type": "string"},
            "currency": {"type": "string"},
            "description": {"type": "string"},
            "idempotency_key": {"type": "string"},
            "workspace_id": {"type": "integer"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "payout_id": {"type": "string"},
            "status": {"type": "string"},
            "transaction_ref": {"type": "string"},
        },
    },
)

FINANCE_TRANSACTION_RECORD_SPEC = CapabilitySpec(
    id="finance.transaction.record",
    name="Record Financial Transaction",
    description="Ghi nhận giao dịch kế toán tài chính vào sổ cái ledger của services/company.",
    risk=CapabilityRisk.MEDIUM,
    input_schema={
        "type": "object",
        "required": ["amount", "account_id", "type"],
        "properties": {
            "amount": {"type": "number"},
            "account_id": {"type": "string"},
            "type": {"type": "string"},
            "description": {"type": "string"},
            "workspace_id": {"type": "integer"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "transaction_id": {"type": "string"},
            "status": {"type": "string"},
        },
    },
)


def create_finance_payout_execute_handler(client: Optional[CompanyServiceClient] = None):
    svc_client = client or CompanyServiceClient()

    async def handle_payout(payload: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        workspace_id = payload.get("workspace_id") or ctx.get("workspace_id", 1)
        body = {
            "workspaceId": workspace_id,
            "amount": payload["amount"],
            "vendor": payload["vendor"],
            "currency": payload.get("currency", "USD"),
            "description": payload.get("description", ""),
            "idempotencyKey": payload["idempotency_key"],
        }
        res = await svc_client.post("/finance-legal/payouts", json=body)
        return res

    return handle_payout


def create_finance_transaction_record_handler(client: Optional[CompanyServiceClient] = None):
    svc_client = client or CompanyServiceClient()

    async def handle_transaction(payload: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        workspace_id = payload.get("workspace_id") or ctx.get("workspace_id", 1)
        body = {
            "workspaceId": workspace_id,
            "amount": payload["amount"],
            "accountId": payload["account_id"],
            "type": payload["type"],
            "description": payload.get("description", ""),
        }
        res = await svc_client.post("/finance-legal/transactions", json=body)
        return res

    return handle_transaction
