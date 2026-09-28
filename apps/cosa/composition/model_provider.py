from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.cosa.models.contracts import ProviderType, ResolvedModelRoute
    from apps.cosa.models.credential_store import LocalCredentialStore
    from apps.cosa.models.providers import ModelClient, ModelProviderFactory

__all__ = [
    "build_credential_store",
    "build_deepseek_model",
    "build_model_provider_factory",
    "build_system_default_model",
    "create_workspace_model_client",
    "system_default_model_configured",
    "system_default_model_identity",
]


_DEFAULT_OPENROUTER_MODEL = "inclusionai/ling-3.0-flash-fin:free"


def build_deepseek_model() -> Any:
    """Dựng `agents.extensions.models.litellm_model.LitellmModel` trỏ tới
    DeepSeek THẬT từ `DEEPSEEK_API_KEY`/`DEEPSEEK_BASE_URL`/
    `DEEPSEEK_DEFAULT_MODEL` — đọc env một chỗ duy nhất tại composition root
    (COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §5.2), không
    rải rác trong kernel.

    Raise RuntimeError rõ ràng nếu thiếu DEEPSEEK_API_KEY — production
    không được silently chạy với model provider chưa cấu hình (§3.2/§5.1).
    """
    if os.environ.get("COSA_MODEL_PROVIDER", "").lower() == "fake":
        from agent_testkit.fake_sdk_model import FakeSDKModel

        return FakeSDKModel()

    # Check environment BEFORE importing LitellmModel, which may load API keys
    # from system config (litellm behavior). We must validate the intentional
    # environment configuration before triggering any external loads.
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "build_deepseek_model() requires DEEPSEEK_API_KEY to be set — "
            "production must not silently run with an unconfigured model "
            "provider. For tests, pass model=<FakeSDKModel instance> "
            "explicitly to build_cosa_agent_plane() or set COSA_MODEL_PROVIDER=fake."
        )

    # Now safe to import LitellmModel after validation
    from agents.extensions.models.litellm_model import LitellmModel

    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    default_model = os.environ.get("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat")

    return LitellmModel(
        model=f"deepseek/{default_model}",
        base_url=base_url,
        api_key=api_key,
    )


def _build_openrouter_model() -> Any:
    """Dựng `LitellmModel` trỏ tới OpenRouter THẬT từ `OPENROUTER_API_KEY`/
    `OPENROUTER_BASE_URL`/`OPENROUTER_DEFAULT_MODEL` — cùng convention với
    `build_deepseek_model()` (đọc env một chỗ duy nhất tại composition
    root). Raise RuntimeError rõ ràng nếu thiếu OPENROUTER_API_KEY — không
    fallback im lặng."""
    if os.environ.get("COSA_MODEL_PROVIDER", "").lower() == "fake":
        from agent_testkit.fake_sdk_model import FakeSDKModel

        return FakeSDKModel()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "build_system_default_model() with COSA_DEFAULT_MODEL_PROVIDER="
            "openrouter requires OPENROUTER_API_KEY to be set — production "
            "must not silently run with an unconfigured model provider. For "
            "tests, pass model=<FakeSDKModel instance> explicitly to "
            "build_cosa_agent_plane() or set COSA_MODEL_PROVIDER=fake."
        )

    from agents.extensions.models.litellm_model import LitellmModel

    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    default_model = os.environ.get("OPENROUTER_DEFAULT_MODEL", _DEFAULT_OPENROUTER_MODEL)

    return LitellmModel(
        model=f"openrouter/{default_model}",
        base_url=base_url,
        api_key=api_key,
    )


def _resolve_system_default_provider() -> str:
    """Parse + validate `COSA_DEFAULT_MODEL_PROVIDER` — hàm DUY NHẤT làm việc
    này, dùng chung bởi `build_system_default_model()`,
    `system_default_model_configured()`, và `system_default_model_identity()`.

    Trước đây mỗi hàm tự parse biến này riêng, và `system_default_model_configured()`
    trả `False` (không raise) cho giá trị lạ trong khi hai hàm còn lại raise
    `RuntimeError` — invariant ngầm bị vi phạm: caller `if not
    system_default_model_configured(): use FakeSDKModel` (worker/main.py,
    api/test_main.py) sẽ ÂM THẦM rơi về FakeSDKModel thay vì fail-closed khi
    `COSA_DEFAULT_MODEL_PROVIDER` bị gõ sai. Gom parse vào một chỗ để cả ba
    hàm luôn đồng nhất: giá trị lạ -> RuntimeError, không có ngoại lệ."""
    provider = os.environ.get("COSA_DEFAULT_MODEL_PROVIDER", "deepseek").strip().lower()
    if provider not in ("deepseek", "openrouter"):
        raise RuntimeError(
            f"Unknown COSA_DEFAULT_MODEL_PROVIDER={provider!r} — expected "
            "'openrouter' or 'deepseek'."
        )
    return provider


def build_system_default_model() -> Any:
    """Composition-root entrypoint DUY NHẤT cho "system default" model client
    (bootstrap khi workspace chưa cấu hình policy/profile nào) — chọn
    provider theo `COSA_DEFAULT_MODEL_PROVIDER` (`openrouter` | `deepseek`,
    không đặt -> `deepseek` để giữ hành vi cũ, không đổi ngầm môi trường khác
    chưa set biến này). Giá trị lạ -> RuntimeError rõ ràng (qua
    `_resolve_system_default_provider()`). Nhánh `COSA_MODEL_PROVIDER=fake`
    (FakeSDKModel) áp dụng cho cả 2 provider, giống `build_deepseek_model()`."""
    provider = _resolve_system_default_provider()
    if provider == "deepseek":
        return build_deepseek_model()
    return _build_openrouter_model()


def system_default_model_configured() -> bool:
    """True nếu credential thật cho system-default provider (theo
    `COSA_DEFAULT_MODEL_PROVIDER`) đã có trong env — dùng ở
    `worker/main.py`/`api/app.py`/`api/test_main.py` để quyết định
    FakeSDKModel vs model thật, KHÔNG tự đọc `DEEPSEEK_API_KEY`/
    `OPENROUTER_API_KEY` rải rác ở các chỗ đó nữa.

    Giá trị lạ ở `COSA_DEFAULT_MODEL_PROVIDER` -> RuntimeError (qua
    `_resolve_system_default_provider()`), CÙNG ngữ nghĩa với
    `build_system_default_model()`/`system_default_model_identity()` — không
    còn trả `False` âm thầm khiến caller rơi về FakeSDKModel khi provider bị
    gõ sai."""
    provider = _resolve_system_default_provider()
    if provider == "openrouter":
        return bool(os.environ.get("OPENROUTER_API_KEY"))
    return bool(os.environ.get("DEEPSEEK_API_KEY"))


def system_default_model_identity() -> tuple[ProviderType, str]:
    """`(ProviderType, model_id)` cho system-default provider hiện tại — dùng
    làm provenance ở `agent_plane.py::SystemDefaultModelProfile`, không đọc
    env provider rải rác ở đó nữa. Giá trị lạ -> RuntimeError (qua
    `_resolve_system_default_provider()`)."""
    from apps.cosa.models.contracts import ProviderType

    provider = _resolve_system_default_provider()
    if provider == "openrouter":
        model_id = os.environ.get("OPENROUTER_DEFAULT_MODEL", _DEFAULT_OPENROUTER_MODEL)
        return ProviderType.OPENROUTER_API, model_id
    model_id = os.environ.get("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat")
    return ProviderType.DEEPSEEK_API, model_id


# ── Task 2 (plan 2026-09-07-local-first-model-routing) — workspace-scoped
# model client, KHÔNG đọc DEEPSEEK_*/provider env cho lựa chọn theo workspace.
#
# `build_deepseek_model()` ở trên VẪN là mechanism hợp lệ cho bootstrap
# "system default" (khi 1 workspace hoàn toàn CHƯA cấu hình policy/profile
# nào — xem `apps.cosa.models.resolver.ModelRouteResolver`/
# `SystemDefaultModelProfile`, do composition layer tiêm env vào MỘT LẦN ở
# đây, không rải rác). Với call đã resolve theo workspace
# (`ResolvedModelRoute` — có `credential_ref` trỏ tới credential thật lưu ở
# `apps.cosa.models.credential_store`), phải đi qua `create_workspace_model_client()`
# bên dưới — không được tự đọc env provider cho case này.


def build_credential_store(session_factory: Any) -> LocalCredentialStore:
    """`session_factory`: SQLAlchemy async session factory thật (cùng convention
    `apps.cosa.models.repository.PostgresModelRoutingRepository`) — bắt buộc
    truyền tường minh, không tự fallback InMemory ở composition root (fallback
    InMemory chỉ hợp lệ trong test, caller test tự dựng
    `LocalCredentialStore(InMemoryCredentialRepository())` trực tiếp)."""
    from apps.cosa.models.credential_store import LocalCredentialStore, PostgresCredentialRepository

    return LocalCredentialStore(PostgresCredentialRepository(session_factory))


def build_model_provider_factory(
    session_factory: Any, *, profile_repository: Any | None = None
) -> ModelProviderFactory:
    from apps.cosa.models.providers import ModelProviderFactory

    store = build_credential_store(session_factory)
    return ModelProviderFactory(store, profile_repository=profile_repository)


async def create_workspace_model_client(
    route: ResolvedModelRoute, *, session_factory: Any, profile_repository: Any | None = None
) -> ModelClient:
    """Composition-root entrypoint cho model client theo workspace đã resolve
    (Task 1 resolver -> Task 2 credential store + adapter factory). Đây là
    đối trọng workspace-scoped của `build_deepseek_model()` — route đã mang
    theo provider_type/model_id/credential_ref xác định, factory KHÔNG tự
    đọc bất kỳ biến môi trường provider nào để chọn route."""
    factory = build_model_provider_factory(session_factory, profile_repository=profile_repository)
    return await factory.create(route)
