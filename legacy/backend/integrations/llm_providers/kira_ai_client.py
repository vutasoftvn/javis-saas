import os
import httpx
from typing import Optional
from integrations.llm_providers._openai_compatible import OpenAICompatibleClient


def get_kira_ai_api_key(workspace_id: Optional[int] = None) -> str:
    """Retrieve Kira AI API key from environment or workspace_secrets."""
    env_key = os.environ.get("KIRAAI_API_KEY", "").strip() or os.environ.get("KIRA_API_KEY", "").strip()
    if env_key:
        return env_key

    if not workspace_id:
        return ""

    try:
        from db.session import SessionLocal
        from integrations.channels.models import WorkspaceSecret
        from core.security import decrypt_secret # type: ignore

        db = SessionLocal()
        try:
            query = db.query(WorkspaceSecret).filter(
                WorkspaceSecret.workspace_id == workspace_id,
                WorkspaceSecret.key.in_(["kira_ai", "kiraai"])
            )
            ws_secret = query.first()
            if ws_secret and ws_secret.encrypted_value:
                try:
                    return decrypt_secret(ws_secret.encrypted_value)
                except Exception:
                    return ws_secret.encrypted_value
            return ""
        finally:
            db.close()
    except Exception:
        return ""


class KiraAIClient(OpenAICompatibleClient):
    """Client for Kira AI Gateway (OpenAI-compatible AI platform in Vietnam)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        workspace_id: int | None = None,
    ):
        if api_key is None:
            api_key = get_kira_ai_api_key(workspace_id)

        actual_base_url = base_url or os.environ.get("KIRAAI_BASE_URL", "https://api.kiraai.vn/v1")
        actual_model = model or os.environ.get("KIRAAI_DEFAULT_MODEL", "deepseek-v4-pro-free")

        super().__init__(
            api_key=api_key,
            base_url=actual_base_url,
            model=actual_model,
            transport=transport,
        )
        self.provider_name = "kira_ai"
        self.api_key = api_key
        self.base_url = actual_base_url
        self.model = actual_model

    @staticmethod
    async def fetch_remote_models(
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> list[str]:
        """Gọi trực tiếp API chuẩn OpenAI GET /v1/models của Kira AI để lấy danh sách model thực tế."""
        key = api_key or os.environ.get("KIRAAI_API_KEY", "").strip() or os.environ.get("KIRA_API_KEY", "").strip()
        url = (base_url or os.environ.get("KIRAAI_BASE_URL", "https://api.kiraai.vn/v1")).rstrip("/")
        headers = {"Authorization": f"Bearer {key}"} if key else {}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{url}/models", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    # Standard OpenAI response: {"data": [{"id": "model_id", ...}]}
                    if isinstance(data, dict) and "data" in data:
                        return [item["id"] for item in data["data"] if isinstance(item, dict) and "id" in item]
        except Exception:
            pass
        return []


