import os
from typing import Optional
from app.automations.runtime.base import AutomationProvider
from app.automations.runtime.adapters.mock import MockAutomationProvider
from app.automations.runtime.adapters.n8n import N8nAdapter


class AutomationRuntimeManager:
    """Singleton managing active AutomationProvider lifecycle and provider selection."""

    def __init__(self) -> None:
        self._provider: Optional[AutomationProvider] = None

    async def start(self) -> None:
        provider_type = os.getenv("COSA_AUTOMATION_PROVIDER", "mock").lower()
        if provider_type == "n8n":
            n8n_url = os.getenv("N8N_BASE_URL", "http://localhost:5678")
            api_key = os.getenv("N8N_API_KEY")
            secret = os.getenv("N8N_WEBHOOK_SECRET", "cosa-n8n-default-secret")
            self._provider = N8nAdapter(base_url=n8n_url, api_key=api_key, webhook_secret=secret)
        else:
            self._provider = MockAutomationProvider()

    async def stop(self) -> None:
        self._provider = None

    def get_provider(self) -> AutomationProvider:
        if self._provider is None:
            self._provider = MockAutomationProvider()
        return self._provider

    def set_provider(self, provider: AutomationProvider) -> None:
        """Utility for testing."""
        self._provider = provider


automation_runtime_manager = AutomationRuntimeManager()
