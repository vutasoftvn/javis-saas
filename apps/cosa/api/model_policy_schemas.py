"""Task 4 (plan 2026-09-07-local-first-model-routing) — request/response schema
cho founder-only model provider/policy settings (`model_policy_routes.py`).

Contract bảo mật bắt buộc (xem task-4 brief): body chỉ dùng `SecretStr` cho
API key (create/rotate) — KHÔNG BAO GIỜ `str` trần, tránh vô tình lọt vào
repr/log. Mọi response model ở đây **CHỈ** trả `credential_configured: bool`
— không bao giờ trả lại API key dưới bất kỳ hình thức nào (kể cả đã mask 1
phần) — model dùng `extra="forbid"` như `ResolvedModelRoute`/
`CredentialReference` (Task 1/2) làm rào chắn cấu trúc.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from apps.cosa.models.contracts import PolicyScope, ProfileStatus, ProviderType

__all__ = [
    "CreateModelProviderRequest",
    "ModelPolicyView",
    "ModelProviderDetailView",
    "SetModelPolicyRequest",
    "TestModelProviderResponse",
]


class CreateModelProviderRequest(BaseModel):
    """Body cho `POST /agent/settings/model-providers`.

    `profile_id` optional — nếu không truyền, server tự sinh (provider_type +
    random suffix) để founder không cần tự nghĩ ID duy nhất. `api_key` dùng
    `SecretStr` — CHỈ được `.get_secret_value()` đúng 1 lần, ngay trước khi
    đưa vào `LocalCredentialStore.put()` (không log, không giữ lại biến
    trung gian dạng `str` trần)."""

    model_config = ConfigDict(extra="forbid")

    provider_type: ProviderType
    profile_id: str | None = None
    model_id: str | None = None
    api_key: SecretStr | None = None
    base_url: str | None = None
    allowed_models: list[str] = Field(default_factory=list)
    budget_usd_limit: float | None = None
    max_concurrency: int | None = None


class ModelProviderDetailView(BaseModel):
    """Response cho create/list provider — KHÔNG BAO GIỜ chứa API key, kể cả
    đã mask. `credential_configured` là cờ duy nhất caller dùng để biết
    provider đã có credential hay chưa."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    provider_type: ProviderType
    model_id: str
    credential_configured: bool
    key_version: int | None = None
    base_url: str | None = None
    allowed_model_ids: list[str] = Field(default_factory=list)
    budget_usd_limit: float | None = None
    max_concurrency: int | None = None
    status: ProfileStatus


class TestModelProviderResponse(BaseModel):
    """Response cho `POST /agent/settings/model-providers/{profile_id}/test`.

    `live_call_attempted` phân biệt rõ 2 tầng kiểm tra (xem task-4-report.md
    phần quyết định "low fixed budget"): tầng 1 luôn chạy (dựng client, giải
    mã credential, validate allowlist/budget/concurrency — không tốn chi phí
    provider); tầng 2 (`live_call_attempted=True`) chỉ chạy cho provider có
    API HTTP-based (LiteLLM) — gọi 1 request thật với `max_tokens=1` để xác
    nhận endpoint/khoá thật sự hoạt động. CLI provider (`claude_cli`/
    `codex_cli`/`gemini_cli`) dừng ở tầng 1 — health-check subprocess CLI
    (login session cục bộ) nằm ngoài phạm vi Task 4 (xem báo cáo)."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    provider_type: ProviderType
    model_id: str
    ok: bool
    live_call_attempted: bool
    detail: str


class SetModelPolicyRequest(BaseModel):
    """Body cho `PUT /agent/settings/model-policies/{agent_profile}`."""

    model_config = ConfigDict(extra="forbid")

    primary_profile_id: str
    fallback_profile_ids: list[str] = Field(default_factory=list)


class ModelPolicyView(BaseModel):
    """Response hiển thị precedence đã resolve (system default > workspace
    default > agent override, theo thứ tự ưu tiên NGƯỢC khi đọc — override
    agent thắng nếu có) cho 1 `agent_profile` — dùng để UI hiển thị
    "route nào đang thực sự áp dụng" mà không cần tự dựng lại logic resolve
    ở phía client (giữ đúng nguyên tắc "display concern, không rebuild logic
    client-side" của Task 4 brief)."""

    model_config = ConfigDict(extra="forbid")

    scope: PolicyScope
    scope_key: str
    primary_profile_id: str
    fallback_profile_ids: list[str] = Field(default_factory=list)
    resolved_profile_id: str
    resolved_provider_type: ProviderType
    resolved_model_id: str
    is_system_default: bool
