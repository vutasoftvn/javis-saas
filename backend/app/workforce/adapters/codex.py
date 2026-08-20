from typing import Any
from app.workforce.extensions.seams import ProviderHealth, ProviderResult

class CodexProvider:
    async def health(self, scope: Any) -> ProviderHealth:
        return ProviderHealth(status="ok")

    async def start(self, scope: Any, config: dict, input_data: dict) -> ProviderResult:
        if not scope.get("sandbox_only", False):
            return ProviderResult(status="error", result="Codex must run in isolated OpenSandbox.")
        return ProviderResult(status="started", result="codex_run_1")

    async def stream(self, scope: Any, run_id: str):
        yield {"event": "started"}

    async def cancel(self, scope: Any, run_id: str) -> bool:
        return True

    async def ingest_artifacts(self, scope: Any, run_id: str) -> list:
        return []
