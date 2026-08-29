import pytest
from apps.cosa.capabilities import finance_write


def test_no_payout_spec_or_handler():
    assert not hasattr(finance_write, "FINANCE_PAYOUT_EXECUTE_SPEC")
    assert not hasattr(finance_write, "create_finance_payout_execute_handler")


def test_transaction_record_spec_contract():
    spec = finance_write.FINANCE_TRANSACTION_RECORD_SPEC
    assert spec.id == "finance.transaction.record"
    schema = spec.input_schema
    assert "workspace_id" in schema["properties"]
    assert "direction" in schema["properties"]
    assert "amount" in schema["properties"]
    assert "description" in schema["properties"]
    assert "direction" in schema["required"]
    assert "amount" in schema["required"]


@pytest.mark.asyncio
async def test_transaction_record_handler_fails_without_workspace_id():
    class FakeClient:
        async def post(self, *a, **k):
            raise AssertionError("should not be called")

    handler = finance_write.create_finance_transaction_record_handler(FakeClient())
    res = await handler(
        {"amount": 100, "direction": "OUT", "description": "test"},
        {},
    )
    assert res.get("success") is False
    assert "workspace_id is required" in res.get("error", "")


@pytest.mark.asyncio
async def test_transaction_record_handler_success():
    calls = []

    class FakeClient:
        async def post(self, path, json):
            calls.append((path, json))
            return {"id": "tx_1", "status": "recorded"}

    handler = finance_write.create_finance_transaction_record_handler(FakeClient())
    res = await handler(
        {
            "workspace_id": "ws_123",
            "amount": 500000,
            "direction": "IN",
            "description": "Customer payment",
        },
        {},
    )
    assert res["id"] == "tx_1"
    assert len(calls) == 1
    path, body = calls[0]
    assert path == "/finance-legal/transactions"
    assert body["workspaceId"] == "ws_123"
    assert body["amount"] == "500000"
    assert body["direction"] == "IN"
