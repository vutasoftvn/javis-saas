from typing import Any, Dict
from workforce.extensions.seams import ProviderHealth, ProviderResult

class N8nProvider:
    async def health(self, scope: Any) -> ProviderHealth:
        return ProviderHealth(status="ok")

    async def start(self, scope: Any, config: dict, input_data: dict) -> ProviderResult:
        # Gọi webhook n8n, truyền correlation_id để nhận lại callback
        return ProviderResult(status="started", result="n8n_run_1")

    async def stream(self, scope: Any, run_id: str):
        # Đợi callback
        yield {"event": "waiting_for_callback"}

    async def cancel(self, scope: Any, run_id: str) -> bool:
        # n8n cancel không support trực tiếp, có thể bỏ qua (idempotent)
        return True

    async def ingest_artifacts(self, scope: Any, run_id: str) -> list:
        return []

    async def handle_callback(self, run_id: str, payload: Dict[str, Any]) -> bool:
        """
        Xử lý callback từ n8n webhook.
        Không cho phép n8n thay đổi trực tiếp workflow state, 
        chỉ trả về data qua callback.
        """
        if payload.get("correlation_id") != run_id:
            return False
        return True
