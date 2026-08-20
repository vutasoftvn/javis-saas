from typing import Any, Callable
from dataclasses import dataclass
from .seams import (
    ConnectorProvider, ModelProvider, ToolBackend, ExecutorProvider,
    SandboxProvider, KnowledgeProvider, EventStore, RuntimeAdapter
)

class ProviderUnavailableError(Exception):
    pass

@dataclass
class SeamEntry:
    provider_type: type
    contract_test: Callable

async def assert_connector_provider_contract(provider: ConnectorProvider):
    # Execute the method so that it raises ProviderUnavailableError if unhealthy
    await provider.discover(scope=None, config={})

def seam_catalog() -> dict[str, SeamEntry]:
    return {
        "model": SeamEntry(ModelProvider, lambda x: None),
        "tool": SeamEntry(ToolBackend, lambda x: None),
        "connector": SeamEntry(ConnectorProvider, assert_connector_provider_contract),
        "executor": SeamEntry(ExecutorProvider, lambda x: None),
        "sandbox": SeamEntry(SandboxProvider, lambda x: None),
        "knowledge": SeamEntry(KnowledgeProvider, lambda x: None),
        "event_store": SeamEntry(EventStore, lambda x: None),
        "runtime": SeamEntry(RuntimeAdapter, lambda x: None),
    }
