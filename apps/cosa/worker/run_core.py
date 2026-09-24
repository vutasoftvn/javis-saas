"""Lõi dùng chung để chuẩn bị + chạy 1 agent run (WGA int. point #2).

Tách từ `_execute_run_task_inner` các bước: resolve AgentSpec exact-hash từ
registry → dựng RunRequest → resolve compliance (mint company delegation) →
`kernel.run`. KHÔNG chứa side-effect UI (stream event, message, artifact,
workforce signal) — caller (`_execute_run_task_inner` cho chat, các handler WGA
cho headless task) tự lo phần I/O của mình.

`resolve_spec` / `prepare_request` raise `RunCoreError(reason_code)` cho mọi lỗi
resolve/compliance; caller map `reason_code` sang message/event của riêng nó
(giữ nguyên hành vi client-facing hiện có ở chat path). Tách 2 hàm để chat path
chèn được 3 UI emit ĐÚNG vị trí cũ (sau resolve spec, trước compliance).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from agent.contracts.run import RunRequest
from agent.contracts.spec import AgentSpec
from agent.registry.repository import SpecDependencyMissingError
from agent.registry.resolver import SpecResolver

from apps.cosa.compliance.contracts import ComplianceDenied
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.models.contracts import ResolvedModelRoute
from apps.cosa.models.providers import ModelProviderMisconfigured
from apps.cosa.observability.otel import trace_span

logger = logging.getLogger(__name__)

__all__ = [
    "RunCoreError",
    "RunCorePrep",
    "apply_compliance",
    "bind_route_to_run",
    "prepare_request",
    "prepare_run",
    "resolve_spec",
    "run_kernel",
]


class RunCoreError(Exception):
    """Lỗi trong lúc chuẩn bị run. `reason_code` là mã ổn định client-safe;
    compliance-denied mang thêm `compliance_code`."""

    def __init__(self, reason_code: str, *, compliance_code: str | None = None) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.compliance_code = compliance_code


@dataclass
class RunCorePrep:
    spec: AgentSpec
    req: RunRequest
    company_delegation_token: str


async def resolve_spec(plane: CosaAgentPlane, *, run_id: str, local_spec: AgentSpec) -> AgentSpec:
    """Resolve exact spec (đúng version + fingerprint) từ registry — không tin
    object Python đang import (có thể drift lúc rolling deploy)."""
    resolver = SpecResolver(repository=plane.spec_registry)
    try:
        resolution = await resolver.resolve_agent_spec_dependencies(local_spec)
    except SpecDependencyMissingError as exc:
        # Không interpolate exception thô (có thể chứa pinned-skill detail) —
        # log server-side đầy đủ, raise mã ổn định.
        logger.exception("agent spec resolution unavailable", extra={"run_id": run_id})
        raise RunCoreError("spec_resolution_unavailable") from exc
    return AgentSpec(**resolution.agent_content)


async def prepare_request(
    plane: CosaAgentPlane,
    *,
    spec: AgentSpec,
    run_id: str,
    prompt: str,
    principal: str,
    workspace_id: str,
    conversation_id: str,
    policy_snapshot: Any | None,
    locale: str = "vi-VN",
    extra_metadata: dict[str, Any] | None = None,
) -> RunCorePrep:
    """Dựng RunRequest + resolve compliance (mint company delegation).

    `policy_snapshot=None` -> không đưa vào metadata (headless task kiểu
    autopilot, không có bearer user để lấy snapshot). Chat path luôn truyền
    snapshot đã resolve trước đó.
    """
    run_metadata: dict[str, Any] = {}
    if policy_snapshot is not None:
        run_metadata["policy_snapshot"] = policy_snapshot.model_dump()
    if extra_metadata:
        run_metadata.update(extra_metadata)
    run_metadata["locale"] = locale

    req = RunRequest(
        run_id=run_id,
        principal=principal,
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": prompt},
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        locale=locale,
        metadata=run_metadata,
    )

    return await apply_compliance(plane, req=req, spec=spec)


async def apply_compliance(
    plane: CosaAgentPlane,
    *,
    req: RunRequest,
    spec: AgentSpec,
    compliance_spec: AgentSpec | None = None,
) -> RunCorePrep:
    """Resolve compliance (mint company delegation) cho 1 RunRequest đã dựng sẵn.

    `compliance_spec` cho phép gate đánh giá theo spec khác với executable — dùng cho
    advisor overlay: overlay không có quyền Project độc lập nên compliance đánh giá theo
    spec của Project deployment (system_key = deployment spec id), chạy executable là overlay.
    """
    compliance_resolver = getattr(plane, "compliance_resolver", None)
    if compliance_resolver is None:
        raise RunCoreError("compliance_resolver_unavailable")

    try:
        compliance_metadata = await compliance_resolver.resolve_for_run(
            req, compliance_spec or spec
        )
    except ComplianceDenied as exc:
        raise RunCoreError("compliance_denied", compliance_code=exc.code) from exc

    if "_company_delegation_token" not in compliance_metadata:
        raise RunCoreError("compliance_denied", compliance_code="MISSING_DELEGATION_TOKEN")

    req.metadata.update(compliance_metadata)
    return RunCorePrep(
        spec=spec,
        req=req,
        company_delegation_token=compliance_metadata["_company_delegation_token"],
    )


async def prepare_run(
    plane: CosaAgentPlane,
    *,
    run_id: str,
    local_spec: AgentSpec,
    prompt: str,
    principal: str,
    workspace_id: str,
    conversation_id: str,
    policy_snapshot: Any | None = None,
    locale: str = "vi-VN",
    extra_metadata: dict[str, Any] | None = None,
) -> RunCorePrep:
    """Tiện ích cho headless caller (WGA task) — resolve_spec + prepare_request
    một lượt, không cần chèn UI emit ở giữa."""
    spec = await resolve_spec(plane, run_id=run_id, local_spec=local_spec)
    return await prepare_request(
        plane,
        spec=spec,
        run_id=run_id,
        prompt=prompt,
        principal=principal,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        policy_snapshot=policy_snapshot,
        locale=locale,
        extra_metadata=extra_metadata,
    )


async def bind_route_to_run(
    resolver: Any, request: RunRequest, spec: AgentSpec
) -> ResolvedModelRoute:
    """Resolve `ResolvedModelRoute` (Task 1) cho 1 run cụ thể.

    Lệch khỏi chữ ký gốc trong task-3 brief
    (`bind_route_to_run(request, spec)`, 2 tham số): resolve thật cần 1
    `ModelRouteResolver` (Task 1) cụ thể để tra cứu policy/profile theo
    workspace, và repo này không có global singleton nào giữ resolver — đúng
    theo composition-root pattern dùng xuyên suốt (CLAUDE.md). Vì vậy hàm
    nhận `resolver` tường minh làm tham số đầu; caller duy nhất (`run_kernel`
    dưới đây) luôn truyền `plane.model_route_resolver`.
    """
    workspace_id = request.workspace_id or ""
    agent_spec_id = getattr(spec, "id", None) or getattr(spec, "spec_id", None) or ""
    return await resolver.resolve_route(workspace_id, agent_spec_id)


def _route_provenance(route: ResolvedModelRoute) -> dict[str, Any]:
    """Provenance ghi vào `RunRequest.model_policy` (persist tới
    `RunRecord.model_policy` — packages/agent/kernel/openai_agents_kernel.py,
    `model_policy=request.model_policy or spec.model_policy`) — CHỈ
    profile_id/provider_type/model_id/fallback/is_system_default, KHÔNG BAO
    GIỜ prompt hay credential (route đã resolve chỉ mang `credential_ref`,
    không phải secret thô — xem apps/cosa/models/contracts.py)."""
    return {
        "workspace_model_route": {
            "profile_id": route.profile_id,
            "provider_type": route.provider_type.value,
            "model_id": route.model_id,
            "fallback_profile_ids": list(route.fallback_profile_ids),
            "is_system_default": route.is_system_default,
        }
    }


async def _build_routed_kernel(plane: CosaAgentPlane, route: ResolvedModelRoute) -> Any:
    """Dựng lại 1 `ExecutionKernel` PER-RUN với model client của
    `route` — tái dùng repository/spec_registry/capability_registry/gateway/
    policy_engine/company_client/compliance_resolver ĐÃ có trên `plane` (rẻ,
    không dựng lại), chỉ đổi `model=`. Xem
    `apps/cosa/composition/kernel_factory.py::build_execution_kernel` param
    `compliance_resolver_override` — bắt buộc truyền `plane.compliance_resolver`
    thật ở đây, KHÔNG để nhánh mặc định của factory tự chuyển sang compliance
    resolver giả chỉ vì `model is not None` (nhánh đó dành cho test/dev).

    `plane.model_provider_factory` được dựng LAZY + cache lại lên plane ngay
    tại đây (không phải lúc `build_cosa_agent_plane()`) — xem ghi chú ở
    `CosaAgentPlane.__init__`.
    """
    factory = plane.model_provider_factory
    if factory is None:
        session_factory = getattr(plane, "model_routing_session_factory", None)
        if session_factory is None:
            raise RunCoreError("model_provider_factory_unavailable")

        from apps.cosa.composition.model_provider import build_model_provider_factory

        factory = build_model_provider_factory(
            session_factory, profile_repository=getattr(plane, "model_routing_repository", None)
        )
        plane.model_provider_factory = factory

    try:
        model_client = await factory.create(route)
    except ModelProviderMisconfigured as exc:
        raise RunCoreError("model_provider_misconfigured") from exc

    from apps.cosa.composition.kernel_factory import build_execution_kernel

    kernel, _ = build_execution_kernel(
        runtime="openai_agents",
        repository=plane.repository,
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
        gateway=plane.gateway,
        policy_engine=plane.policy_engine,
        company_client=plane.company_client,
        model=model_client,
        compliance_resolver_override=plane.compliance_resolver,
    )
    return kernel


async def run_kernel(
    plane: CosaAgentPlane,
    prep: RunCorePrep,
    *,
    workspace_id: str,
    run_id: str,
) -> tuple[Any, float]:
    """Gọi kernel.run trong trace span; trả (run_result, duration_sec).

    Task 3 (plan 2026-09-07-local-first-model-routing) — nếu `plane` có
    `model_route_resolver` (mọi plane build qua `build_cosa_agent_plane()`
    kể từ Task 3 đều có; `SimpleNamespace` test double không set field này ->
    `getattr(..., None)` giữ nguyên hành vi CŨ, dùng thẳng `plane.kernel`),
    resolve route TRƯỚC khi chạy và ghi provenance vào `prep.req.model_policy`.
    Route `is_system_default=True` (workspace CHƯA cấu hình policy/profile
    nào) tiếp tục dùng `plane.kernel` KHÔNG THAY ĐỔI — model client của nó đã
    được `build_execution_kernel()` dựng đúng 1 lần lúc khởi động process
    (system-default bootstrap, xem `apps/cosa/composition/model_provider.py`).
    Chỉ khi route KHÔNG phải system-default (workspace đã cấu hình
    policy/profile thật) mới dựng 1 kernel per-run mới qua
    `_build_routed_kernel()`.

    QUAN TRỌNG: hàm này chỉ được gọi SAU khi `prepare_request()` đã compliance-
    approve run (raise `RunCoreError("compliance_denied", ...)` nếu deny,
    caller — `apps/cosa/worker/handlers.py` — return sớm không bao giờ gọi
    tới đây) — route resolution + model client construction (kể cả subprocess
    CLI bridge) luôn nằm SAU compliance gate, không bao giờ trước.
    """
    kernel = plane.kernel
    resolver = getattr(plane, "model_route_resolver", None)
    if resolver is not None:
        route = await bind_route_to_run(resolver, prep.req, prep.spec)
        prep.req.model_policy = _route_provenance(route)
        if not route.is_system_default:
            kernel = await _build_routed_kernel(plane, route)

    _start = time.monotonic()
    async with trace_span(
        "kernel.run",
        attributes={
            "run_id": run_id,
            "agent_spec_id": getattr(prep.spec, "spec_id", None),
            "workspace_id": workspace_id,
        },
    ):
        run_result = await kernel.run(prep.req, prep.spec)
    return run_result, time.monotonic() - _start
