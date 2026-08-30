from __future__ import annotations

from unittest.mock import AsyncMock
import pytest

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.marketing_write import (
    CAMPAIGN_ASSET_WRITE_SPEC,
    EXPERIMENT_WRITE_SPEC,
    create_campaign_asset_write_handler,
    create_experiment_write_handler,
)


@pytest.mark.asyncio
async def test_campaign_asset_write_anti_bypass():
    client = AsyncMock(spec=CompanyServiceClient)
    handler = create_campaign_asset_write_handler(client)

    # 1. Valid internal asset write
    res = await handler(
        {
            "asset_name": "Landing Page Copy v1",
            "content": "# Hero Headline\nSupercharge your workflow",
            "asset_type": "copy",
        },
        context={"workspace_id": "ws-1"},
    )
    assert res["status"] == "saved"
    assert "artifact://ws-1/campaign-assets/" in res["object_ref"]

    # 2. Attempt to publish to public_url is rejected
    with pytest.raises(ValueError, match="publishing to public_url is not permitted"):
        await handler(
            {
                "asset_name": "Public Page",
                "content": "Content",
                "public_url": "https://example.com/live",
            },
            context={"workspace_id": "ws-1"},
        )


@pytest.mark.asyncio
async def test_experiment_write_requires_metric_contract_and_rejects_spend():
    client = AsyncMock(spec=CompanyServiceClient)
    handler = create_experiment_write_handler(client)

    # 1. Valid experiment write
    res = await handler(
        {
            "hypothesis": "Value proposition A increases conversion by 15%",
            "metric": "conversion_rate",
            "metric_contract_id": "contract-val-001",
            "target_value": 0.15,
        },
        context={"workspace_id": "ws-1"},
    )
    assert res["status"] == "pending_approval"
    assert res["metric_contract_id"] == "contract-val-001"

    # 2. Missing metric_contract_id is rejected
    with pytest.raises(ValueError, match="requires a valid metric_contract_id"):
        await handler(
            {
                "hypothesis": "Ungrounded experiment",
                "metric": "conversion_rate",
            },
            context={"workspace_id": "ws-1"},
        )

    # 3. Attempting to spend / budget or auto-activate is rejected
    with pytest.raises(ValueError, match="cannot modify budget/spend or auto-activate"):
        await handler(
            {
                "hypothesis": "Ad campaign experiment",
                "metric": "clicks",
                "metric_contract_id": "contract-1",
                "spend": 500,
            },
            context={"workspace_id": "ws-1"},
        )
