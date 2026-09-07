"""Task 2 (plan 2026-09-07-local-first-model-routing) — `ModelProviderFactory`:
ánh xạ `ResolvedModelRoute` (Task 1) -> client model thật (`ModelClient`,
duck-typed tương thích interface `agents.Model`/`LitellmModel` đã dùng ở
`apps/cosa/composition/model_provider.py::build_deepseek_model()`).

Validate TRƯỚC khi build client, theo đúng thứ tự: (1) allowed_models
allowlist, (2) provider_type có adapter hay không, (3) credential thuộc ĐÚNG
workspace của route (structural — `LocalCredentialStore.get()` tự fail-closed
qua AAD, factory không tự giải mã). Không tự bịa field không có trên
`ResolvedModelRoute` (contract `extra="forbid"` — xem contracts.py) để enforce
budget_usd_limit/max_concurrency; những field đó tồn tại trên
`ModelProviderProfile` (Task 1) chứ KHÔNG có trên route đã resolve — factory
này nhận optional `profile_repository` để tra cứu lại profile gốc và validate
budget/concurrency/status ngay trước khi build client, thay vì âm thầm bỏ qua
hoặc sửa contract Task 1 ngoài phạm vi Task 2 (xem task-2-report.md).

Compliance egress data class (loại dữ liệu được phép rời COSA) đã có tầng
riêng ở `apps/cosa/compliance/resolver.py::ComplianceResolver` — resolve theo
từng RunRequest, không phải theo model client. Factory này KHÔNG lặp lại
logic đó (tránh 2 nơi cùng quyết định 1 việc) — nó chỉ đảm bảo: credential
không rò rỉ vào error/log, và route không được build client nếu thiếu
credential bắt buộc.

CLI providers (`claude_cli`/`codex_cli`/`gemini_cli`) là bridge subprocess —
Task 3 sở hữu implementation thật. Factory raise `NotImplementedError` rõ
ràng, không fallback ngầm sang provider khác.
"""

from __future__ import annotations

from typing import Any

from apps.cosa.models.contracts import ProviderType, ResolvedModelRoute
from apps.cosa.models.credential_store import CredentialNotFound

__all__ = [
    "ModelClient",
    "ModelProviderFactory",
    "ModelProviderMisconfigured",
]

# Duck-typed: bất kỳ object nào tương thích interface `agents.Model` (model=
# truyền được cho openai-agents SDK) — cùng cách `build_deepseek_model()` trả
# `Any` thay vì 1 type cụ thể, vì các adapter (LitellmModel, CLI bridge Task 3,
# …) không chia sẻ 1 base class chung trong repo hiện tại.
ModelClient = Any

_LITELLM_PREFIX_BY_PROVIDER: dict[ProviderType, str] = {
    ProviderType.ANTHROPIC_API: "anthropic",
    ProviderType.OPENAI_API: "openai",
    ProviderType.OPENROUTER_API: "openrouter",
    ProviderType.DEEPSEEK_API: "deepseek",
}

_CLI_PROVIDERS = frozenset(
    {ProviderType.CLAUDE_CLI, ProviderType.CODEX_CLI, ProviderType.GEMINI_CLI}
)

# openai_api là credential type RIÊNG — ChatGPT subscription (đăng nhập
# CODEX_CLI qua tài khoản) KHÔNG phải credential OPENAI_API (ràng buộc toàn
# cục của plan, xem task-2 brief). Không dùng chung nhánh với CODEX_CLI.


class ModelProviderMisconfigured(Exception):
    """Route yêu cầu credential còn thiếu/không hợp lệ, model không nằm trong
    allowlist, hoặc profile gốc vi phạm budget/concurrency/status. Message
    KHÔNG BAO GIỜ chứa plaintext secret — chỉ credential_ref/profile_id."""


class ModelProviderFactory:
    def __init__(self, credential_store: Any, *, profile_repository: Any | None = None) -> None:
        self._credentials = credential_store
        self._profile_repository = profile_repository

    async def create(self, route: ResolvedModelRoute) -> ModelClient:
        self._validate_allowed_models(route)
        await self._validate_profile_limits(route)

        if route.provider_type in _CLI_PROVIDERS:
            raise NotImplementedError(
                f"{route.provider_type.value} CLI bridge chưa triển khai ở Task 2 — "
                "xem Task 3 (docs/superpowers/plans/2026-09-07-local-first-model-routing.md)."
            )

        if route.provider_type == ProviderType.LOCAL_OPENAI_COMPATIBLE:
            return await self._create_local_openai_compatible(route)

        if route.provider_type in _LITELLM_PREFIX_BY_PROVIDER:
            return await self._create_litellm_client(route)

        raise ModelProviderMisconfigured(
            f"provider_type '{route.provider_type.value}' không được hỗ trợ bởi "
            "ModelProviderFactory."
        )

    # ── validation trước khi build client ──

    def _validate_allowed_models(self, route: ResolvedModelRoute) -> None:
        if route.allowed_models and route.model_id not in route.allowed_models:
            raise ModelProviderMisconfigured(
                f"model_id '{route.model_id}' không nằm trong allowlist của profile "
                f"'{route.profile_id}' (workspace='{route.workspace_id}')."
            )

    async def _validate_profile_limits(self, route: ResolvedModelRoute) -> None:
        """Tra cứu lại `ModelProviderProfile` gốc (nếu factory được tiêm
        `profile_repository`) để chặn budget/concurrency/status TRƯỚC khi
        build client — field này không có trên `ResolvedModelRoute` (Task 1
        cố ý chỉ giữ field tối thiểu, `extra="forbid"`), nên phải tra cứu lại
        thay vì đọc thẳng từ route."""
        if self._profile_repository is None:
            return

        from apps.cosa.models.contracts import ProfileStatus

        profile = await self._profile_repository.get_profile(route.workspace_id, route.profile_id)
        if profile is None:
            raise ModelProviderMisconfigured(
                f"profile '{route.profile_id}' không còn tồn tại trong workspace "
                f"'{route.workspace_id}' — không thể build client cho route đã resolve."
            )
        if profile.status != ProfileStatus.ACTIVE:
            raise ModelProviderMisconfigured(
                f"profile '{route.profile_id}' không còn ACTIVE — từ chối build client."
            )
        if profile.budget_usd_limit is not None and profile.budget_usd_limit <= 0:
            raise ModelProviderMisconfigured(
                f"profile '{route.profile_id}' đã hết budget_usd_limit — từ chối build client."
            )
        if profile.max_concurrency is not None and profile.max_concurrency <= 0:
            raise ModelProviderMisconfigured(
                f"profile '{route.profile_id}' đã đạt max_concurrency=0 — từ chối build client."
            )

    async def _resolve_credential(self, route: ResolvedModelRoute) -> str:
        if not route.credential_ref:
            raise ModelProviderMisconfigured(
                f"provider '{route.provider_type.value}' yêu cầu credential (API key) nhưng "
                f"route (workspace='{route.workspace_id}', profile='{route.profile_id}') không "
                "có credential_ref."
            )
        try:
            secret = await self._credentials.get(route.workspace_id, route.credential_ref)
        except CredentialNotFound as exc:
            raise ModelProviderMisconfigured(
                f"credential_ref='{route.credential_ref}' không tìm thấy hoặc không thuộc "
                f"workspace '{route.workspace_id}'."
            ) from exc
        return secret.get_secret_value()

    # ── adapter cụ thể ──

    async def _create_litellm_client(self, route: ResolvedModelRoute) -> ModelClient:
        api_key = await self._resolve_credential(route)
        from agents.extensions.models.litellm_model import LitellmModel

        prefix = _LITELLM_PREFIX_BY_PROVIDER[route.provider_type]
        return LitellmModel(model=f"{prefix}/{route.model_id}", api_key=api_key)

    async def _create_local_openai_compatible(self, route: ResolvedModelRoute) -> ModelClient:
        # Self-hosted/local endpoint — credential là optional (mạng nội bộ
        # không cần auth). Nếu route có credential_ref thì vẫn resolve và
        # validate workspace scoping giống các provider khác. `base_url` là
        # routing metadata KHÔNG phải secret (xem contracts.py) — truyền
        # thẳng vào LitellmModel khi route có cấu hình; không bịa default nào
        # thay caller nếu thiếu (None -> LitellmModel dùng default của chính
        # nó / caller phải tự cấu hình).
        api_key = "local-no-auth"
        if route.credential_ref:
            api_key = await self._resolve_credential(route)

        from agents.extensions.models.litellm_model import LitellmModel

        kwargs: dict[str, Any] = {"model": f"openai/{route.model_id}", "api_key": api_key}
        if route.base_url:
            kwargs["base_url"] = route.base_url
        return LitellmModel(**kwargs)
