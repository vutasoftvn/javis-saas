import pytest

from app.workforce.memory.health import UNAVAILABLE, check_sidecar_health


@pytest.mark.asyncio
async def test_check_sidecar_health_unavailable_when_nothing_listens():
    """No memory sidecar is running in this dev environment (by design - it
    is optional infrastructure, ADR-MEM-002) - the health check must report
    UNAVAILABLE rather than raising or hanging."""
    health = await check_sidecar_health(base_url="http://127.0.0.1:8765", timeout_seconds=0.5)

    assert health.status == UNAVAILABLE
    assert health.latency_ms is None
    assert health.backend == "tencentdb_agent_memory"
    assert health.last_error is not None
