from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from apps.cosa.capabilities.finance_read import (
    FINANCE_CONNECTION_READ_SPEC,
    FINANCE_TRANSACTION_READ_SPEC,
    create_finance_connection_read_handler,
    create_finance_transaction_read_handler,
)
from apps.cosa.capabilities.finance_write import (
    FINANCE_TRANSACTION_CLASSIFY_PROPOSE_SPEC,
    FINANCE_ACCOUNTING_DOCUMENT_CREATE_DRAFT_SPEC,
    FINANCE_ACCOUNTING_DOCUMENT_CONFIRM_SPEC,
    create_finance_transaction_classify_propose_handler,
    create_finance_accounting_document_create_draft_handler,
    create_finance_accounting_document_confirm_handler,
)


@pytest.mark.asyncio
async def test_finance_read_handlers():
    client = AsyncMock()
    client.get.side_effect = [
        {"connections": [{"id": "1", "provider": "cas", "consentState": "GRANTED"}]},
        {"transactions": [{"id": "10", "amount": "5000000", "direction": "IN"}]},
    ]

    conn_handler = create_finance_connection_read_handler(client)
    res_conn = await conn_handler({"workspace_id": 1001}, context=None)
    assert len(res_conn["connections"]) == 1
    assert res_conn["connections"][0]["provider"] == "cas"

    txn_handler = create_finance_transaction_read_handler(client)
    res_txn = await txn_handler({"workspace_id": 1001, "status": "UNRECONCILED"}, context=None)
    assert len(res_txn["transactions"]) == 1
    assert res_txn["transactions"][0]["amount"] == "5000000"


@pytest.mark.asyncio
async def test_finance_write_handlers():
    client = AsyncMock()
    client.post.side_effect = [
        {"id": "prop_1", "status": "PENDING"},
        {"id": "doc_1", "status": "DRAFT", "number": "PT-001"},
        {"id": "doc_1", "status": "CONFIRMED", "number": "PT-001"},
    ]

    classify_handler = create_finance_transaction_classify_propose_handler(client)
    prop_res = await classify_handler(
        {
            "workspace_id": 1001,
            "bank_transaction_id": "txn_1",
            "accounting_document_id": "doc_1",
            "confidence": 0.95,
        },
        context=None,
    )
    assert prop_res["proposal"]["id"] == "prop_1"
    assert prop_res["advisory"]["layer"] == "CURRENT_LAW"
    assert prop_res["advisory"]["label"] == "proposal"

    draft_handler = create_finance_accounting_document_create_draft_handler(client)
    draft_res = await draft_handler(
        {
            "workspace_id": 1001,
            "document_type": "RECEIPT",
            "number": "PT-001",
            "document_date": "2026-08-29",
            "amount": 2500000,
            "description": "Thu tien dich vu",
        },
        context=None,
    )
    assert draft_res["document"]["status"] == "DRAFT"
    assert draft_res["advisory"]["layer"] == "CURRENT_LAW"

    confirm_handler = create_finance_accounting_document_confirm_handler(client)
    confirm_res = await confirm_handler(
        {"workspace_id": 1001, "document_id": "doc_1"},
        context=None,
    )
    assert confirm_res["document"]["status"] == "CONFIRMED"
