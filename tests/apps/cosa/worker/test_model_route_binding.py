"""Task 3 (plan 2026-09-07-local-first-model-routing) — model route binding
trong `apps/cosa/worker/run_core.py`: `bind_route_to_run()` resolve
`ResolvedModelRoute`, `run_kernel()` dựng lại kernel per-run khi route KHÔNG
phải system-default, và persist provenance vào `RunRequest.model_policy`.

Dùng đúng convention nhẹ đã có ở `tests/apps/cosa/wga/test_run_core.py`
(`SimpleNamespace` làm test double cho `plane`, không cần dựng
`build_cosa_agent_plane()` đầy đủ) — 1 `SimpleNamespace` không set field mới
(`model_route_resolver`) mô phỏng đúng plane build TRƯỚC Task 3, chứng minh
hành vi cũ (dùng thẳng `plane.kernel`, không resolve route) không đổi.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from apps.cosa.compliance.contracts import ComplianceDenied
from apps.cosa.models.contracts import ProviderType, ResolvedModelRoute
from apps.cosa.models.providers import ModelProviderMisconfigured
from apps.cosa.worker.run_core import (
    RunCoreError,
    bind_route_to_run,
    prepare_request,
    run_kernel,
)


def _spec():
    return SimpleNamespace(
        id="cosa.agents.operations",
        spec_id="cosa.agents.operations",
        to_pinned_identity=lambda: "cosa.agents.operations@1.0.0#hash",
    )


def _system_default_route() -> ResolvedModelRoute:
    return ResolvedModelRoute(
        workspace_id="ws-a",
        agent_spec_id="cosa.agents.operations",
        profile_id="system-default",
        provider_type=ProviderType.DEEPSEEK_API,
        model_id="deepseek-chat",
        credential_ref=None,
        fallback_profile_ids=(),
        is_system_default=True,
    )


def _configured_route(provider_type: ProviderType = ProviderType.CLAUDE_CLI) -> ResolvedModelRoute:
    return ResolvedModelRoute(
        workspace_id="ws-a",
        agent_spec_id="cosa.agents.operations",
        profile_id="profile-claude",
        provider_type=provider_type,
        model_id="claude-something",
        credential_ref=None,
        fallback_profile_ids=("profile-fallback",),
        is_system_default=False,
    )


class _SpyModelProviderFactory:
    def __init__(self, client=None, error: Exception | None = None) -> None:
        self.calls: list[ResolvedModelRoute] = []
        self._client = client if client is not None else object()
        self._error = error

    async def create(self, route: ResolvedModelRoute):
        self.calls.append(route)
        if self._error:
            raise self._error
        return self._client


@pytest.mark.asyncio
async def test_bind_route_to_run_uses_resolver_with_workspace_and_spec_id():
    resolver = AsyncMock()
    resolver.resolve_route.return_value = _system_default_route()
    request = SimpleNamespace(workspace_id="ws-a")

    route = await bind_route_to_run(resolver, request, _spec())

    resolver.resolve_route.assert_awaited_once_with("ws-a", "cosa.agents.operations")
    assert route.is_system_default is True


@pytest.mark.asyncio
async def test_run_kernel_uses_plane_kernel_when_no_resolver_configured():
    """Backward-compat: plane KHÔNG có `model_route_resolver` (test double cũ,
    hoặc plane build từ trước Task 3) -> hành vi giữ nguyên y hệt trước đây,
    không resolve route, không gọi model_provider_factory."""
    kernel = AsyncMock()
    kernel.run.return_value = SimpleNamespace(status="completed")
    plane = SimpleNamespace(kernel=kernel)
    prep = SimpleNamespace(spec=_spec(), req=SimpleNamespace(model_policy={}))

    result, _duration = await run_kernel(plane, prep, workspace_id="ws-a", run_id="r1")

    assert result.status == "completed"
    kernel.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_kernel_uses_plane_kernel_for_system_default_route_and_never_touches_factory():
    kernel = AsyncMock()
    kernel.run.return_value = SimpleNamespace(status="completed")
    resolver = AsyncMock()
    resolver.resolve_route.return_value = _system_default_route()
    spy_factory = _SpyModelProviderFactory()
    plane = SimpleNamespace(
        kernel=kernel, model_route_resolver=resolver, model_provider_factory=spy_factory
    )
    prep = SimpleNamespace(spec=_spec(), req=SimpleNamespace(workspace_id="ws-a", model_policy={}))

    result, _duration = await run_kernel(plane, prep, workspace_id="ws-a", run_id="r1")

    assert result.status == "completed"
    kernel.run.assert_awaited_once()
    assert spy_factory.calls == []
    assert prep.req.model_policy["workspace_model_route"]["is_system_default"] is True
    assert prep.req.model_policy["workspace_model_route"]["profile_id"] == "system-default"


@pytest.mark.asyncio
async def test_run_kernel_builds_routed_kernel_for_non_system_default_route(monkeypatch):
    """Route KHÔNG phải system-default (workspace đã cấu hình policy/profile
    thật) -> `run_kernel` phải: (1) gọi `model_provider_factory.create(route)`
    đúng 1 lần với route đã resolve, (2) dựng kernel MỚI qua
    `build_execution_kernel(model=<client vừa tạo>, ...)` (không dùng
    `plane.kernel` cũ), (3) chạy `.run()` trên kernel MỚI đó."""
    old_kernel = AsyncMock()
    new_kernel = AsyncMock()
    new_kernel.run.return_value = SimpleNamespace(status="completed")

    route = _configured_route()
    resolver = AsyncMock()
    resolver.resolve_route.return_value = route
    spy_factory = _SpyModelProviderFactory(client="fake-cli-bridge-model")

    captured_kwargs: dict = {}

    def _fake_build_execution_kernel(**kwargs):
        captured_kwargs.update(kwargs)
        return new_kernel, "mock-compliance-resolver-should-not-matter"

    monkeypatch.setattr(
        "apps.cosa.composition.kernel_factory.build_execution_kernel",
        _fake_build_execution_kernel,
    )

    real_compliance_resolver = object()
    plane = SimpleNamespace(
        kernel=old_kernel,
        model_route_resolver=resolver,
        model_provider_factory=spy_factory,
        repository=object(),
        spec_registry=object(),
        capability_registry=object(),
        gateway=object(),
        policy_engine=object(),
        company_client=object(),
        compliance_resolver=real_compliance_resolver,
    )
    prep = SimpleNamespace(spec=_spec(), req=SimpleNamespace(workspace_id="ws-a", model_policy={}))

    result, _duration = await run_kernel(plane, prep, workspace_id="ws-a", run_id="r1")

    assert result.status == "completed"
    old_kernel.run.assert_not_awaited()
    new_kernel.run.assert_awaited_once()
    assert spy_factory.calls == [route]
    assert captured_kwargs["model"] == "fake-cli-bridge-model"
    # Compliance_resolver_override PHẢI là resolver THẬT của plane — không để
    # build_execution_kernel tự chuyển sang mock chỉ vì model is not None.
    assert captured_kwargs["compliance_resolver_override"] is real_compliance_resolver
    assert prep.req.model_policy["workspace_model_route"]["profile_id"] == "profile-claude"
    assert prep.req.model_policy["workspace_model_route"]["fallback_profile_ids"] == [
        "profile-fallback"
    ]


@pytest.mark.asyncio
async def test_run_kernel_fails_closed_when_routed_provider_misconfigured():
    resolver = AsyncMock()
    resolver.resolve_route.return_value = _configured_route()
    spy_factory = _SpyModelProviderFactory(error=ModelProviderMisconfigured("bad profile"))
    plane = SimpleNamespace(
        kernel=AsyncMock(),
        model_route_resolver=resolver,
        model_provider_factory=spy_factory,
    )
    prep = SimpleNamespace(spec=_spec(), req=SimpleNamespace(workspace_id="ws-a", model_policy={}))

    with pytest.raises(RunCoreError) as ei:
        await run_kernel(plane, prep, workspace_id="ws-a", run_id="r1")

    assert ei.value.reason_code == "model_provider_misconfigured"


@pytest.mark.asyncio
async def test_compliance_deny_prevents_adapter_invocation():
    """Brief step 1 test — 1 provider bị compliance từ chối phải nhận ĐÚNG 0
    prompt request. Chứng minh bằng control flow THẬT (không chỉ assertion
    tách rời): `prepare_request()` raise `RunCoreError("compliance_denied")`
    TRƯỚC khi bất kỳ route/model-provider nào được chạm tới — model route
    resolution + adapter/subprocess invocation chỉ nằm trong `run_kernel()`,
    được gọi SAU `prepare_request()` trong toàn bộ code path thật
    (`apps/cosa/worker/handlers.py`); ở đây ta lặp lại đúng thứ tự đó."""
    resolver = AsyncMock()
    resolver.resolve_route.return_value = _configured_route(ProviderType.CLAUDE_CLI)
    spy_factory = _SpyModelProviderFactory()

    denying_compliance_resolver = AsyncMock()
    denying_compliance_resolver.resolve_for_run.side_effect = ComplianceDenied(
        "DATA_EGRESS_BLOCKED"
    )

    plane = SimpleNamespace(
        compliance_resolver=denying_compliance_resolver,
        kernel=AsyncMock(),
        model_route_resolver=resolver,
        model_provider_factory=spy_factory,
    )

    with pytest.raises(RunCoreError) as ei:
        prep = await prepare_request(
            plane,
            spec=_spec(),
            run_id="r1",
            prompt="do something risky",
            principal="user_1",
            workspace_id="ws-a",
            conversation_id="c1",
            policy_snapshot=None,
        )
        # Nếu prepare_request KHÔNG raise (bug), dòng dưới mới chạm tới
        # run_kernel — cố tình để lộ rõ nếu ordering bị phá vỡ trong tương lai.
        await run_kernel(plane, prep, workspace_id="ws-a", run_id="r1")

    assert ei.value.reason_code == "compliance_denied"
    assert ei.value.compliance_code == "DATA_EGRESS_BLOCKED"
    # Khẳng định chính: provider factory (và do đó CLI bridge/subprocess bên
    # dưới nó) chưa từng được gọi — "denied provider gets zero prompt
    # requests".
    assert spy_factory.calls == []
    resolver.resolve_route.assert_not_awaited()
