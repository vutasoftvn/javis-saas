import pytest
import asyncio
from workforce.extensions.contracts import (
    assert_connector_provider_contract,
    ProviderUnavailableError,
    seam_catalog,
)
from workforce.extensions.seams import ConnectorProvider

class FakeConnectorProvider(ConnectorProvider):
    def __init__(self, healthy: bool):
        self._healthy = healthy

    async def health(self, scope):
        from workforce.extensions.seams import ProviderHealth
        return ProviderHealth(status="ok" if self._healthy else "error")

    async def discover(self, scope, config):
        if not self._healthy:
            raise ProviderUnavailableError()
        return ()

    async def invoke(self, scope, capability_id, arguments):
        if not self._healthy:
            raise ProviderUnavailableError()
        return None

def test_connector_provider_contract_rejects_unhealthy_discovery():
    provider = FakeConnectorProvider(healthy=False)
    with pytest.raises(ProviderUnavailableError):
        asyncio.run(assert_connector_provider_contract(provider))

def test_every_seam_has_interface_provider_consumer_and_contract_entry():
    catalog = seam_catalog()
    assert set(catalog) == {"model", "tool", "connector", "executor", "sandbox", "knowledge", "event_store", "runtime"}
    assert all(item.contract_test for item in catalog.values())
