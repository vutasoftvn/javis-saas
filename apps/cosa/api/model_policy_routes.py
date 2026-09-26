"""Task 4 (plan 2026-09-07-local-first-model-routing) — founder-only REST
commands cho model provider/policy settings (`/agent/settings/model-*`).

Cùng convention với `apps/cosa/api/settings_routes.py`: `APIRouter(prefix=
"/agent/settings", ...)`, `MvpSuccess`/`mvp_item`/`mvp_list` envelope,
`AuthenticatedIdentity`/`get_authenticated_identity`/`require_workspace_
operator`. Khác với settings_routes.py (state ở COSA Control Plane) — dữ
liệu ở đây (`models.model_provider_profiles`/`models.workspace_model_
policies`/`models.workspace_credentials`) là Agent Platform's OWN Postgres
(migration 030-032, `apps.cosa.models.repository`/`credential_store`), nên
`source_kind` trong mvp-surface.json là `agent_db`, không phải
`control_plane`.

Bảo mật (Global Constraint #4 của plan + brief Task 4):
  - Mọi mutation (create/rotate provider, set policy) bắt buộc
    `require_workspace_operator` — member GET được (member chỉ đọc status,
    không xem/đổi secret — đúng thiết kế "Member chỉ đọc status nếu policy
    cho phép, không xem hoặc thay secret").
  - `CreateModelProviderRequest.api_key` là `SecretStr` — chỉ
    `.get_secret_value()` đúng 1 lần, ngay trước khi đưa vào
    `LocalCredentialStore.put()`.
  - Không response nào (kể cả lỗi) chứa API key dưới bất kỳ hình thức nào —
    chỉ `credential_configured: bool`.
"""

from __future__ import annotations

import logging
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.api.model_policy_schemas import (
    CreateModelProviderRequest,
    ModelPolicyView,
    ModelProviderDetailView,
    SetModelPolicyRequest,
    TestModelProviderResponse,
)
from apps.cosa.api.mvp_response import MvpSourceRef, MvpSuccess, mvp_item, mvp_list
from apps.cosa.auth import (
    AuthenticatedIdentity,
    get_authenticated_identity,
    require_workspace_operator,
)
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.models.contracts import (
    ModelRouteNotFound,
    PolicyScope,
    ProviderType,
    ResolvedModelRoute,
)
from apps.cosa.models.credential_store import CredentialNotFound

logger = logging.getLogger("cosa.api.model_policy")

router = APIRouter(prefix="/agent/settings", tags=["settings", "model-routing"])

SOURCE_AGENT_DB = MvpSourceRef(kind="agent_db", ref="models.model_provider_profiles")
SOURCE_AGENT_DB_POLICY = MvpSourceRef(kind="agent_db", ref="models.workspace_model_policies")

# Tầng 2 (live call) của test-connection: budget CỐ ĐỊNH, thấp nhất có thể —
# `max_tokens=1` là budget nhỏ nhất litellm còn chấp nhận cho hầu hết
# provider chat completion (không có cách "0 token" mà vẫn thực sự gọi round
# trip HTTP tới provider). Đây là quyết định tường minh của Task 4 cho câu
# "low fixed budget" trong brief — xem task-4-report.md.
_TEST_CONNECTION_MAX_TOKENS = 1
_TEST_CONNECTION_PROMPT = "ping"
# Timeout ngắn dành riêng cho tầng live-call CLI (subprocess) — không dùng
# `CliBridgeModel` default (120s, tối ưu cho 1 câu trả lời agent thật) vì test-
# connection chỉ cần biết CLI khởi động/trả lời được, không cần đợi lâu.
# Claude Code cần khởi động Node + 1 round-trip API (thường 5-15s) — 10s cũ
# làm test-connection báo lỗi giả dù CLI hoạt động bình thường.
_TEST_CONNECTION_CLI_TIMEOUT_SECONDS = 45.0

# Provider có thể gọi thật qua litellm.acompletion với endpoint OpenAI-style.
_LITELLM_TESTABLE_PROVIDERS = frozenset(
    {
        ProviderType.ANTHROPIC_API,
        ProviderType.OPENAI_API,
        ProviderType.OPENROUTER_API,
        ProviderType.DEEPSEEK_API,
        ProviderType.LOCAL_OPENAI_COMPATIBLE,
    }
)

_LITELLM_PREFIX_BY_PROVIDER: dict[ProviderType, str] = {
    ProviderType.ANTHROPIC_API: "anthropic",
    ProviderType.OPENAI_API: "openai",
    ProviderType.OPENROUTER_API: "openrouter",
    ProviderType.DEEPSEEK_API: "deepseek",
    ProviderType.LOCAL_OPENAI_COMPATIBLE: "openai",
}


def _get_plane(request: Request) -> CosaAgentPlane:
    plane = getattr(request.app.state, "plane", None) or getattr(
        request.app.state, "cosa_agent_plane", None
    )
    if plane is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CosaAgentPlane is not initialized",
        )
    return plane


def _get_model_routing_repository(plane: CosaAgentPlane) -> Any:
    repo = getattr(plane, "model_routing_repository", None)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="model routing repository is not initialized",
        )
    return repo


def _get_credential_store(plane: CosaAgentPlane) -> Any:
    """Dựng `LocalCredentialStore` LAZY, cache lại NGAY LÊN `plane` — cùng
    pattern lazy-cache-on-plane với `plane.model_provider_factory`
    (`apps/cosa/worker/run_core.py`): `LocalCredentialStore.__init__` eagerly
    đọc/tạo key file cục bộ (side effect), không nên trả giá đó cho mọi
    process khởi động chỉ vì có route founder-only tồn tại."""
    store = getattr(plane, "_model_settings_credential_store", None)
    if store is not None:
        return store

    session_factory = getattr(plane, "model_routing_session_factory", None)
    if session_factory is not None:
        from apps.cosa.composition.model_provider import build_credential_store

        store = build_credential_store(session_factory)
    else:
        # InMemory fallback (dev/test không cấu hình AGENT_DATABASE_URL) —
        # cùng convention `apps.cosa.models.repository.InMemoryModelRoutingRepository`.
        from apps.cosa.models.credential_store import (
            InMemoryCredentialRepository,
            LocalCredentialStore,
        )

        store = LocalCredentialStore(InMemoryCredentialRepository())

    plane._model_settings_credential_store = store  # type: ignore[attr-defined]
    return store


def _generate_profile_id(provider_type: ProviderType) -> str:
    return f"{provider_type.value}-{secrets.token_hex(4)}"


def _to_detail_view(profile: Any) -> ModelProviderDetailView:
    return ModelProviderDetailView(
        profile_id=profile.profile_id,
        provider_type=profile.provider_type,
        model_id=profile.model_id,
        credential_configured=bool(profile.credential_ref),
        key_version=None,
        base_url=profile.base_url,
        allowed_model_ids=list(profile.allowed_models),
        budget_usd_limit=profile.budget_usd_limit,
        max_concurrency=profile.max_concurrency,
        status=profile.status,
    )


@router.post("/model-providers", status_code=status.HTTP_201_CREATED)
async def create_model_provider(
    body: CreateModelProviderRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[ModelProviderDetailView]:
    """Tạo (hoặc upsert) 1 `ModelProviderProfile` cho workspace của founder.

    Founder-only (`require_workspace_operator`). `api_key` (nếu có) được mã
    hoá qua `LocalCredentialStore.put()` — chỉ `credential_ref` (ID) được lưu
    vào `models.model_provider_profiles`, KHÔNG BAO GIỜ giá trị thô."""
    require_workspace_operator(identity)
    plane = _get_plane(request)
    repo = _get_model_routing_repository(plane)

    profile_id = body.profile_id or _generate_profile_id(body.provider_type)

    credential_ref: str | None = None
    if body.api_key is not None:
        store = _get_credential_store(plane)
        # Truyền THẲNG `SecretStr` xuống `LocalCredentialStore.put()` — route
        # này KHÔNG tự gọi `.get_secret_value()` (chỉ nơi DUY NHẤT gọi hàm đó
        # là bên trong `put()`, xem apps/cosa/models/credential_store.py —
        # Task 2). Không có biến trung gian nào ở đây từng cầm plaintext.
        credential_ref_obj = await store.put(identity.workspace_id, body.api_key)
        credential_ref = credential_ref_obj.id

    try:
        profile = await repo.create_profile(
            identity.workspace_id,
            profile_id,
            body.provider_type,
            model_id=body.model_id,
            credential_ref=credential_ref,
            base_url=body.base_url,
            allowed_models=tuple(body.allowed_models),
            budget_usd_limit=body.budget_usd_limit,
            max_concurrency=body.max_concurrency,
        )
    except Exception as exc:
        logger.exception("model_provider_create_failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="model routing repository unavailable",
        ) from exc

    return mvp_item(_to_detail_view(profile), [SOURCE_AGENT_DB])


@router.get("/model-providers")
async def list_model_providers(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[ModelProviderDetailView]]:
    """Đọc danh sách provider profile của workspace — member đọc được (chỉ
    status/metadata, không secret); mutation vẫn founder-only."""
    plane = _get_plane(request)
    repo = _get_model_routing_repository(plane)

    list_fn = getattr(repo, "list_profiles", None)
    if list_fn is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="model routing repository does not support listing profiles",
        )
    profiles = await list_fn(identity.workspace_id)
    return mvp_list([_to_detail_view(p) for p in profiles], [SOURCE_AGENT_DB])


@router.post("/model-providers/{profile_id}/test")
async def test_model_provider(
    profile_id: str,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[TestModelProviderResponse]:
    """Kiểm tra kết nối 1 provider profile — founder-only.

    2 tầng (xem `TestModelProviderResponse` docstring):
      1. Luôn chạy: dựng `ModelClient` thật qua `ModelProviderFactory.create()`
         — validate allowlist/budget/concurrency/status VÀ giải mã credential
         thành công (không tốn chi phí provider, không gọi mạng ra ngoài).
      2. Chỉ cho provider HTTP-based (LiteLLM): gọi 1 request thật, budget cố
         định `max_tokens=1` — xác nhận endpoint/khoá THẬT SỰ hoạt động.
    Client (Flutter) không được tự suy luận "usable" — phải đợi
    `ok=true` từ đúng endpoint này."""
    require_workspace_operator(identity)
    plane = _get_plane(request)
    repo = _get_model_routing_repository(plane)

    profile = await repo.get_profile(identity.workspace_id, profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"profile '{profile_id}' không tồn tại trong workspace này",
        )

    route = ResolvedModelRoute(
        workspace_id=identity.workspace_id,
        agent_spec_id="__settings_test_connection__",
        profile_id=profile.profile_id,
        provider_type=profile.provider_type,
        model_id=profile.model_id,
        credential_ref=profile.credential_ref,
        base_url=profile.base_url,
        allowed_models=profile.allowed_models,
        fallback_profile_ids=(),
        is_system_default=False,
    )

    factory = getattr(plane, "model_provider_factory", None)
    if factory is None:
        from apps.cosa.composition.model_provider import build_model_provider_factory

        session_factory = getattr(plane, "model_routing_session_factory", None)
        if session_factory is not None:
            factory = build_model_provider_factory(session_factory, profile_repository=repo)
        else:
            from apps.cosa.models.providers import ModelProviderFactory

            factory = ModelProviderFactory(_get_credential_store(plane), profile_repository=repo)
        plane.model_provider_factory = factory

    try:
        client = await factory.create(route)
    except Exception as exc:
        # `ModelProviderMisconfigured`/`CredentialNotFound` message đã được
        # kiểm soát (không chứa plaintext secret — xem providers.py/
        # credential_store.py) nên an toàn để trả về caller.
        return mvp_item(
            TestModelProviderResponse(
                profile_id=profile_id,
                provider_type=profile.provider_type,
                model_id=profile.model_id,
                ok=False,
                live_call_attempted=False,
                detail=str(exc),
            ),
            [SOURCE_AGENT_DB],
        )

    if profile.provider_type not in _LITELLM_TESTABLE_PROVIDERS:
        # CLI provider: tầng 2 gọi thật `CliBridge.invoke()` với 1 prompt tối
        # giản + timeout ngắn (final-review finding #2 — trước fix này hàm
        # LUÔN trả `ok=True` chỉ vì dựng được `CliBridgeModel`, không hề spawn
        # subprocess; 1 profile trỏ executable không tồn tại vẫn báo "usable").
        ok, detail = await _run_cli_live_test_call(client)
        return mvp_item(
            TestModelProviderResponse(
                profile_id=profile_id,
                provider_type=profile.provider_type,
                model_id=profile.model_id,
                ok=ok,
                live_call_attempted=True,
                detail=detail,
            ),
            [SOURCE_AGENT_DB],
        )

    ok, detail = await _run_live_test_call(client, profile)
    return mvp_item(
        TestModelProviderResponse(
            profile_id=profile_id,
            provider_type=profile.provider_type,
            model_id=profile.model_id,
            ok=ok,
            live_call_attempted=True,
            detail=detail,
        ),
        [SOURCE_AGENT_DB],
    )


async def _run_live_test_call(client: Any, profile: Any) -> tuple[bool, str]:
    """Gọi 1 request litellm thật, budget cố định (`max_tokens=1`). Đọc
    `api_key`/`base_url` từ chính `client` (LitellmModel) đã dựng — KHÔNG giải
    mã credential lần 2 ở đây (tránh 2 nơi cùng cầm plaintext)."""
    try:
        import litellm

        api_key = getattr(client, "api_key", None)
        base_url = getattr(client, "base_url", None)
        model_name = getattr(client, "model", None) or (
            f"{_LITELLM_PREFIX_BY_PROVIDER[profile.provider_type]}/{profile.model_id}"
        )
        kwargs: dict[str, Any] = {
            "model": model_name,
            "messages": [{"role": "user", "content": _TEST_CONNECTION_PROMPT}],
            "max_tokens": _TEST_CONNECTION_MAX_TOKENS,
        }
        if api_key is not None:
            kwargs["api_key"] = api_key
        if base_url is not None:
            kwargs["base_url"] = base_url

        await litellm.acompletion(**kwargs)
        return True, "live call thành công"
    except Exception as exc:  # provider/network lỗi -> ok=False, không raise
        # Không đưa `api_key`/header thô vào detail — chỉ str(exc). litellm
        # tự redact phần lớn, nhưng KHÔNG tin tuyệt đối: log chi tiết đầy đủ
        # ở server (logger.exception), chỉ trả message rút gọn cho caller.
        logger.exception("model_provider_test_connection_live_call_failed")
        return False, f"live call thất bại: {type(exc).__name__}"


# Sentinel cho scope_key WORKSPACE-level — path param `agent_profile` là ID
# 1 agent_spec_id CỤ THỂ (vd. "operations") theo interface của brief; muốn set
# default TOÀN WORKSPACE, caller truyền sentinel này thay vì 1 agent_spec_id
# thật. Không dùng chuỗi rỗng/None (path param FastAPI không cho phép rỗng) —
# xem quyết định trong task-4-report.md.
WORKSPACE_DEFAULT_SENTINEL = "_workspace_default"


def _resolve_agent_spec_id(agent_profile: str) -> str:
    """Map path param `agent_profile` (short, human-friendly — vd
    `"operations"`) sang `agent_spec_id` THẬT (`spec.id`, vd
    `"cosa.agents.operations"`) mà runtime dùng để resolve route
    (`apps/cosa/worker/run_core.py::bind_route_to_run` gọi
    `getattr(spec, "id", ...)`, KHÔNG PHẢI raw `agent_profile`).

    Dùng CHUNG `AGENT_PROFILE_SPECS` (apps/cosa/agents/agent_profile_specs.py
    — cùng bảng `apps/cosa/worker/handlers.py` dùng để dispatch run thật,
    tách ra module nhẹ riêng để route này không phải kéo theo toàn bộ import
    chain của `handlers.py`) — bảng ánh xạ DUY NHẤT quyết định agent_profile
    nào ứng với AgentSpec nào (CLAUDE.md: "Chọn spec nào cho 1 agent_profile
    là bảng ánh xạ tường minh... thêm agent_profile mới PHẢI thêm vào bảng
    này"). Trước fix này, route lưu/đọc policy thẳng dưới `agent_profile`
    ngắn — lệch khỏi `agent_spec_id` dài mà `bind_route_to_run` thực sự tra
    cứu lúc chạy, khiến override AGENT_PROFILE không bao giờ được áp dụng
    (final-review finding #1). Raise 404 nếu `agent_profile` không nằm trong
    bảng — KHÔNG âm thầm coi `agent_profile` là chính `agent_spec_id` (tránh
    lặp lại đúng bug đó dưới dạng khác)."""
    spec = AGENT_PROFILE_SPECS.get(agent_profile)
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"agent_profile '{agent_profile}' không được hỗ trợ — không có "
                "AgentSpec ánh xạ trong _AGENT_PROFILE_SPECS."
            ),
        )
    spec_id = getattr(spec, "id", None) or getattr(spec, "spec_id", None)
    if not spec_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AgentSpec cho '{agent_profile}' thiếu id/spec_id.",
        )
    return str(spec_id)


def _resolve_policy_lookup_key(agent_profile: str) -> str:
    """`agent_profile` path param -> key dùng để resolve/tra policy.
    `WORKSPACE_DEFAULT_SENTINEL` đi thẳng (không phải 1 AgentSpec thật —
    `resolve_route`/`get_policy` với key này luôn miss ở scope AGENT_PROFILE
    rồi rơi xuống scope WORKSPACE, đúng ý nghĩa "workspace default"); mọi giá
    trị khác PHẢI có mặt trong `_AGENT_PROFILE_SPECS`."""
    if agent_profile == WORKSPACE_DEFAULT_SENTINEL:
        return agent_profile
    return _resolve_agent_spec_id(agent_profile)


async def _run_cli_live_test_call(client: Any) -> tuple[bool, str]:
    """Gọi 1 request `CliBridge` THẬT (subprocess) qua chính `CliBridgeModel`
    đã dựng ở tầng 1 — prompt tối giản (`_TEST_CONNECTION_PROMPT`), timeout
    ngắn (`_TEST_CONNECTION_CLI_TIMEOUT_SECONDS`).

    Đọc `_bridge`/`_executable`/`_model_id`/`_profile_id` thẳng từ `client`
    (attribute riêng của `CliBridgeModel`, không phải interface công khai) —
    cùng cách tiếp cận với `_run_live_test_call` đọc `client.api_key`/
    `client.base_url` của `LitellmModel`: route này CỐ TÌNH tái dùng client
    đã dựng ở tầng 1 thay vì decrypt/build lại lần 2.

    KHÔNG BAO GIỜ trả `stderr` thô của CLI ra caller — chỉ `type(exc).__name__`
    (xem `CliBridgeExecutionError` — message của nó có thể chứa tới 2000 ký tự
    stderr, coi là an toàn cho SERVER LOG, KHÔNG an toàn để echo cho client).
    Lỗi đầy đủ luôn được log server-side qua `logger.exception`."""
    from apps.cosa.models.cli_bridge import ModelInvocation

    bridge = getattr(client, "_bridge", None)
    executable = getattr(client, "_executable", None)
    if bridge is None or executable is None:
        return False, "CLI bridge client không hợp lệ — thiếu bridge/executable nội bộ"

    model_id = getattr(client, "_model_id", None)
    profile_id = getattr(client, "_profile_id", "default")

    try:
        await bridge.invoke(
            ModelInvocation(
                executable=executable,
                prompt=_TEST_CONNECTION_PROMPT,
                model_id=model_id,
                timeout_seconds=_TEST_CONNECTION_CLI_TIMEOUT_SECONDS,
                profile_id=profile_id,
            )
        )
        return True, "live call thành công (CLI)"
    except Exception as exc:  # CliBridgeDenied/ModelProviderTimeout/CliBridgeExecutionError/...
        logger.exception("model_provider_test_connection_cli_live_call_failed")
        return False, f"live call thất bại: {type(exc).__name__}"


async def _lookup_policy_provenance(
    repo: Any, workspace_id: str, agent_profile: str
) -> tuple[PolicyScope, str, str, list[str]] | None:
    """Tra lại (KHÔNG resolve lại route) chính sách nào (nếu có) đang xác định
    route cho `agent_profile` — để hiển thị đúng scope/scope_key/fallback đã
    lưu, tách biệt khỏi việc route cuối cùng resolve ra sao (đã có sẵn qua
    `ModelRouteResolver.resolve_route`). Trả `None` nếu KHÔNG có policy nào
    (route đang dùng system default)."""
    policy = await repo.get_policy(workspace_id, PolicyScope.AGENT_PROFILE, agent_profile)
    if policy is None:
        policy = await repo.get_policy(workspace_id, PolicyScope.WORKSPACE, workspace_id)
    if policy is None:
        return None
    return (
        policy.scope,
        policy.scope_key,
        policy.primary_profile_id,
        list(policy.fallback_profile_ids),
    )


@router.get("/model-policies/{agent_profile}")
async def get_model_policy(
    agent_profile: str,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[ModelPolicyView]:
    """Đọc route đã resolve cho `agent_profile` — hiển thị precedence
    (AGENT_PROFILE override > WORKSPACE default > system default) VÀ fallback
    tường minh. Member đọc được (read-only status)."""
    plane = _get_plane(request)
    resolver = getattr(plane, "model_route_resolver", None)
    if resolver is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="model route resolver is not initialized",
        )
    repo = _get_model_routing_repository(plane)

    lookup_key = _resolve_policy_lookup_key(agent_profile)

    try:
        resolved = await resolver.resolve_route(identity.workspace_id, lookup_key)
    except ModelRouteNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    provenance = await _lookup_policy_provenance(repo, identity.workspace_id, lookup_key)
    fallback_ids: list[str]
    if provenance is None:
        scope, scope_key, primary_id, fallback_ids = (
            PolicyScope.WORKSPACE,
            identity.workspace_id,
            resolved.profile_id,
            [],
        )
    else:
        scope, scope_key, primary_id, fallback_ids = provenance

    view = ModelPolicyView(
        scope=scope,
        scope_key=scope_key,
        primary_profile_id=primary_id,
        fallback_profile_ids=fallback_ids,
        resolved_profile_id=resolved.profile_id,
        resolved_provider_type=resolved.provider_type,
        resolved_model_id=resolved.model_id,
        is_system_default=resolved.is_system_default,
    )
    return mvp_item(view, [SOURCE_AGENT_DB_POLICY])


@router.put("/model-policies/{agent_profile}")
async def set_model_policy(
    agent_profile: str,
    body: SetModelPolicyRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[ModelPolicyView]:
    """Set policy cho 1 agent_profile (override) hoặc toàn workspace (default,
    dùng sentinel `WORKSPACE_DEFAULT_SENTINEL`). Founder-only.

    Fail-closed: `primary_profile_id`/`fallback_profile_ids` phải tồn tại
    ĐÚNG trong workspace này (đã enforce ở
    `ModelRouteResolver`/repository.set_policy — Task 1), không tự tạo
    profile mới ở đây."""
    require_workspace_operator(identity)
    plane = _get_plane(request)
    resolver = getattr(plane, "model_route_resolver", None)
    if resolver is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="model route resolver is not initialized",
        )

    if agent_profile == WORKSPACE_DEFAULT_SENTINEL:
        lookup_key = agent_profile
    else:
        # Map agent_profile ngắn (vd "operations") sang agent_spec_id thật
        # (vd "cosa.agents.operations") TRƯỚC khi set_policy — xem
        # `_resolve_agent_spec_id` docstring cho lý do (final-review finding
        # #1: lệch key giữa REST write path và `bind_route_to_run` read path).
        lookup_key = _resolve_agent_spec_id(agent_profile)

    try:
        if agent_profile == WORKSPACE_DEFAULT_SENTINEL:
            policy = await resolver.set_workspace_default(
                identity.workspace_id,
                body.primary_profile_id,
                tuple(body.fallback_profile_ids),
            )
        else:
            policy = await resolver.set_agent_override(
                identity.workspace_id,
                lookup_key,
                body.primary_profile_id,
                tuple(body.fallback_profile_ids),
            )
    except ModelRouteNotFound as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except CredentialNotFound as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    resolved = await resolver.resolve_route(identity.workspace_id, lookup_key)
    view = ModelPolicyView(
        scope=policy.scope,
        scope_key=policy.scope_key,
        primary_profile_id=policy.primary_profile_id,
        fallback_profile_ids=list(policy.fallback_profile_ids),
        resolved_profile_id=resolved.profile_id,
        resolved_provider_type=resolved.provider_type,
        resolved_model_id=resolved.model_id,
        is_system_default=resolved.is_system_default,
    )
    return mvp_item(view, [SOURCE_AGENT_DB_POLICY])


def create_model_policy_router() -> APIRouter:
    """Factory trả router — cùng convention `create_skill_registry_router()`
    (file này chọn factory thay vì chỉ export `router` trực tiếp như
    `settings_routes.py`, vì `app.py` đã import nhiều router theo factory
    pattern cho các router "mới hơn" — xem `create_skill_registry_router`,
    `create_conversation_router`, v.v. trong app.py)."""
    return router
