import os

import httpx

from app.integrations.llm_providers._openai_compatible import OpenAICompatibleClient


class OpenRouterClient(OpenAICompatibleClient):
    """Khoá lấy theo thứ tự: tham số > ``OPENROUTER_API_KEY`` > khoá workspace đã lưu.

    Nhánh thứ ba là bắt buộc chứ không phải tiện thể: người dùng cấu hình OpenRouter ngay
    trong app (POST /api/v1/ai/openrouter-key, lưu mã hoá vào ``workspace_secrets``), và
    ``is_provider_configured`` đã tính khoá đó là "đã cấu hình" - model picker hiện tích
    xanh, brain-api chọn openrouter làm mặc định. Nếu chỗ gọi model thật lại chỉ đọc biến
    môi trường thì cả hệ thống nói "đã cấu hình" trong khi mọi lượt gọi đều chết ở
    ``provider_not_configured``, và AI chỉ chạy được chừng nào còn ai đó nhớ export khoá
    vào container - dựng lại container là mất.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        workspace_id: int | None = None,
    ):
        if api_key is None:
            api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            # Import tại chỗ: openrouter_service kéo theo model_registry và session DB,
            # không cần thiết cho các client khác dùng chung module này.
            from app.integrations.llm_providers.openrouter_service import get_openrouter_api_key

            api_key = get_openrouter_api_key(workspace_id)

        super().__init__(
            api_key=api_key,
            base_url=base_url or os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            model=model or os.environ.get("OPENROUTER_DEFAULT_MODEL", "openrouter/auto"),
            transport=transport,
        )
