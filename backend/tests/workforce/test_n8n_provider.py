import pytest
from workforce.adapters.n8n import N8nProvider

@pytest.mark.asyncio
async def test_n8n_provider_contract():
    provider = N8nProvider()
    
    scope = {}
    
    result = await provider.start(scope, {}, {"webhook_url": "http://localhost/webhook"})
    assert result.status == "started"
    
    cancel_result = await provider.cancel(scope, "n8n_run_1")
    assert cancel_result is True

@pytest.mark.asyncio
async def test_n8n_callback_correlation():
    """Test n8n callback processing must use correlation id and signature."""
    provider = N8nProvider()
    
    callback_payload = {
        "correlation_id": "n8n_run_1",
        "output": {"status": "success"}
    }
    
    # Callback xử lý idempotent và trả về qua stream/result
    result = await provider.handle_callback("n8n_run_1", callback_payload)
    assert result == True
