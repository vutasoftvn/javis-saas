"""Fallback model lúc chạy theo fallback_profile_ids (spec reliability hạng mục 2)."""

from __future__ import annotations

from typing import Any

import pytest
from agents.models.interface import Model as SdkModel

from apps.cosa.models.contracts import ProfileStatus, ProviderType, SystemDefaultModelProfile
from apps.cosa.models.fallback_model import FallbackModel
from apps.cosa.models.repository import InMemoryModelRoutingRepository
from apps.cosa.models.resolver import ModelRouteResolver

pytestmark = pytest.mark.asyncio


class AuthenticationError(Exception):
    """Cùng tên class với litellm.AuthenticationError."""


class _Fake(SdkModel):
    def __init__(self, name: str, error: Exception | None = None, fail_at: int = 0) -> None:
        self.name = name
        self.error = error
        self.fail_at = fail_at  # stream: lỗi ngay trước event thứ fail_at
        self.calls = 0

    async def get_response(self, *args: Any, **kwargs: Any) -> Any:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return f"response:{self.name}"

    async def stream_response(self, *args: Any, **kwargs: Any):
        self.calls += 1
        for i in range(2):
            if self.error is not None and i == self.fail_at:
                raise self.error
            yield f"{self.name}:{i}"


def _factory(model: SdkModel):
    async def _create() -> SdkModel:
        return model

    return _create


async def test_insufficient_balance_falls_back_and_sticks_to_working_profile():
    primary = _Fake("p", Exception("litellm.BadRequestError: Insufficient Balance"))
    backup = _Fake("b")
    seen: list[tuple[str, str, str]] = []
    m = FallbackModel(
        primary,
        primary_profile_id="p",
        fallbacks=[("b", _factory(backup))],
        on_fallback=lambda a, b, c: seen.append((a, b, c)),
    )

    assert await m.get_response() == "response:b"
    assert await m.get_response() == "response:b"
    assert primary.calls == 1  # lượt sau không thử lại primary đã hỏng
    assert seen == [("p", "b", "provider_insufficient_balance")]
    assert m.fallback_events == [
        {"from": "p", "to": "b", "reason": "provider_insufficient_balance"}
    ]


async def test_auth_error_detected_by_exception_class_name():
    m = FallbackModel(
        _Fake("p", AuthenticationError("bad key")),
        primary_profile_id="p",
        fallbacks=[("b", _factory(_Fake("b")))],
    )
    assert await m.get_response() == "response:b"


@pytest.mark.parametrize(
    "error",
    [
        Exception("litellm.RateLimitError: 429 Too Many Requests"),
        ValueError("unknown variables: ['query']"),
    ],
)
async def test_non_fallback_errors_are_raised_unchanged(error):
    backup = _Fake("b")
    m = FallbackModel(
        _Fake("p", error), primary_profile_id="p", fallbacks=[("b", _factory(backup))]
    )
    with pytest.raises(type(error)):
        await m.get_response()
    assert backup.calls == 0


async def test_all_fallbacks_fail_raises_last_error_and_skips_unbuildable_profile():
    async def broken() -> SdkModel:
        raise RuntimeError("misconfigured")

    last = _Fake("c", Exception("503 Service Unavailable"))
    m = FallbackModel(
        _Fake("p", Exception("503 Service Unavailable")),
        primary_profile_id="p",
        fallbacks=[("b", broken), ("c", _factory(last))],
    )
    with pytest.raises(Exception, match="503"):
        await m.get_response()
    assert last.calls == 1
    assert [e["to"] for e in m.fallback_events] == ["c"]


async def test_stream_falls_back_only_before_first_event():
    before = FallbackModel(
        _Fake("p", Exception("Insufficient Balance"), fail_at=0),
        primary_profile_id="p",
        fallbacks=[("b", _factory(_Fake("b")))],
    )
    assert [e async for e in before.stream_response()] == ["b:0", "b:1"]

    after = FallbackModel(
        _Fake("p", Exception("Insufficient Balance"), fail_at=1),
        primary_profile_id="p",
        fallbacks=[("b", _factory(_Fake("b")))],
    )
    got: list[str] = []
    with pytest.raises(Exception, match="Insufficient Balance"):
        async for e in after.stream_response():
            got.append(e)
    assert got == ["p:0"]  # không ghép câu trả lời của model khác giữa chừng


async def test_resolver_returns_active_fallbacks_after_the_chosen_profile():
    sd = SystemDefaultModelProfile(
        profile_id="sd",
        provider_type=ProviderType.LOCAL_OPENAI_COMPATIBLE,
        model_id="m",
        allowed_models=("m",),
    )
    r = ModelRouteResolver(InMemoryModelRoutingRepository(), sd)
    await r.create_profile("ws", "primary", ProviderType.OPENAI_API)
    await r.create_profile("ws", "f1", ProviderType.ANTHROPIC_API)
    await r.create_profile("ws", "f2", ProviderType.OPENAI_API, status=ProfileStatus.DISABLED)
    await r.create_profile("ws", "f3", ProviderType.OPENAI_API)
    await r.set_workspace_default("ws", "primary", ["f1", "f2", "f3"])

    route = await r.resolve_route("ws", "cosa.agents.operations")
    assert [x.profile_id for x in await r.resolve_fallback_routes(route)] == ["f1", "f3"]

    # primary disabled -> route chính là f1; fallback chỉ còn các profile SAU f1
    await r.create_profile("ws2", "primary", ProviderType.OPENAI_API, status=ProfileStatus.DISABLED)
    await r.create_profile("ws2", "f1", ProviderType.OPENAI_API)
    await r.create_profile("ws2", "f3", ProviderType.OPENAI_API)
    await r.set_workspace_default("ws2", "primary", ["f1", "f3"])
    route2 = await r.resolve_route("ws2", "cosa.agents.operations")
    assert route2.profile_id == "f1"
    assert [x.profile_id for x in await r.resolve_fallback_routes(route2)] == ["f3"]

    sd_route = await r.resolve_route("ws-none", "cosa.agents.operations")
    assert await r.resolve_fallback_routes(sd_route) == []


async def test_build_routed_kernel_wraps_model_only_when_policy_has_fallbacks(monkeypatch):
    from types import SimpleNamespace

    from apps.cosa.worker import run_core

    captured: dict[str, Any] = {}

    def fake_build_execution_kernel(**kwargs):
        captured["model"] = kwargs["model"]
        return "kernel", None

    monkeypatch.setattr(
        "apps.cosa.composition.kernel_factory.build_execution_kernel",
        fake_build_execution_kernel,
    )
    sd = SystemDefaultModelProfile(
        profile_id="sd",
        provider_type=ProviderType.LOCAL_OPENAI_COMPATIBLE,
        model_id="m",
        allowed_models=("m",),
    )
    resolver = ModelRouteResolver(InMemoryModelRoutingRepository(), sd)
    await resolver.create_profile("ws", "primary", ProviderType.OPENAI_API)
    await resolver.create_profile("ws", "backup", ProviderType.OPENAI_API)
    await resolver.set_workspace_default("ws", "primary", ["backup"])
    await resolver.create_profile("ws-solo", "primary", ProviderType.OPENAI_API)
    await resolver.set_workspace_default("ws-solo", "primary", [])

    created: list[str] = []

    class _Factory:
        async def create(self, route):
            created.append(route.profile_id)
            return _Fake(route.profile_id)

    plane = SimpleNamespace(
        model_provider_factory=_Factory(),
        model_route_resolver=resolver,
        repository=None,
        spec_registry=None,
        capability_registry=None,
        gateway=None,
        policy_engine=None,
        company_client=None,
        compliance_resolver=None,
    )

    route = await resolver.resolve_route("ws", "cosa.agents.operations")
    await run_core._build_routed_kernel(plane, route)
    model = captured["model"]
    assert isinstance(model, FallbackModel)
    assert created == ["primary"]  # fallback dựng lazy, chỉ khi cần

    solo = await resolver.resolve_route("ws-solo", "cosa.agents.operations")
    await run_core._build_routed_kernel(plane, solo)
    assert isinstance(captured["model"], _Fake)
