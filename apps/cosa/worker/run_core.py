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

import functools
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
    project_id: str | None = None,
    initiative_id: str | None = None,
    history: list[dict[str, str]] | None = None,
    compliance_spec: AgentSpec | None = None,
    session_ref: str | None = None,
) -> RunCorePrep:
    """Dựng RunRequest + resolve compliance (mint company delegation).

    `compliance_spec`: agent workspace (clone của built-in) được đánh giá compliance theo spec
    built-in gốc — dùng lại đúng binding catalog AI system của agent gốc.

    `policy_snapshot=None` -> không đưa vào metadata (headless task kiểu
    autopilot, không có bearer user để lấy snapshot). Chat path luôn truyền
    snapshot đã resolve trước đó.
    """
    run_metadata: dict[str, Any] = {}
    if policy_snapshot is not None:
        run_metadata["policy_snapshot"] = policy_snapshot.model_dump()
    if extra_metadata:
        run_metadata.update(extra_metadata)
    # project_id tường minh (đã verify ở backend) thắng extra_metadata — kernel
    # dùng nó cho session_context trong prompt và apply_run_scope của tool.
    if project_id:
        run_metadata["project_id"] = str(project_id)
    if initiative_id:
        run_metadata["initiative_id"] = str(initiative_id)
    run_metadata["locale"] = locale

    req = RunRequest(
        run_id=run_id,
        principal=principal,
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": prompt, **({"history": history} if history else {})},
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        session_ref=session_ref,
        locale=locale,
        metadata=run_metadata,
    )

    if initiative_id:
        from apps.cosa.governance.initiative_policy import assert_initiative_run_allowed

        store = getattr(plane, "ai_initiative_snapshot_store", None)
        snapshot = (
            await store.get_current(workspace_id, str(initiative_id)) if store is not None else None
        )
        if snapshot is None:
            # Run tagged với initiative_id nhưng KHÔNG có snapshot promotion nào
            # (chưa từng promote, hoặc store chưa wire) — fail closed, không
            # âm thầm bỏ qua policy gate (trước đây skip hoàn toàn ở đây).
            raise RunCoreError(
                "initiative_snapshot_not_found",
                compliance_code="INITIATIVE_SNAPSHOT_NOT_FOUND",
            )
        decision = assert_initiative_run_allowed(snapshot, req)
        if not decision.allowed:
            raise RunCoreError(
                decision.reason_code,
                compliance_code=decision.reason_code.upper(),
            )
        if decision.initiative_revision is not None:
            run_metadata["initiative_revision"] = decision.initiative_revision
        if decision.autonomy_tier is not None:
            run_metadata["autonomy_tier"] = decision.autonomy_tier
        if decision.risk_tier is not None:
            run_metadata["risk_tier"] = decision.risk_tier
        if decision.decision_hash:
            run_metadata["decision_hash"] = decision.decision_hash

    return await apply_compliance(plane, req=req, spec=spec, compliance_spec=compliance_spec)


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
    project_id: str | None = None,
    initiative_id: str | None = None,
    compliance_spec: AgentSpec | None = None,
) -> RunCorePrep:
    """Tiện ích cho headless caller (WGA task) — resolve_spec + prepare_request
    một lượt, không cần chèn UI emit ở giữa.

    Business run phải có scope Project (quy tắc 14): thiếu `project_id` thì
    raise `RunCoreError("missing_project_scope")`, không suy diễn project.
    """
    if not project_id:
        raise RunCoreError("missing_project_scope")
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
        project_id=project_id,
        initiative_id=initiative_id,
        compliance_spec=compliance_spec,
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
    # Agent workspace không có model policy riêng: route theo agent built-in gốc.
    metadata = getattr(spec, "metadata", None) or {}
    agent_spec_id = metadata.get("origin_agent_spec_id") or agent_spec_id
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
    kernel, _model = await _build_routed_kernel_with_model(plane, route)
    return kernel


async def _build_routed_kernel_with_model(
    plane: CosaAgentPlane, route: ResolvedModelRoute
) -> tuple[Any, Any]:
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

    # Fallback lúc chạy (spec reliability hạng mục 2): lỗi provider khi gọi
    # model chuyển sang profile kế tiếp trong allowlist của policy.
    resolver = getattr(plane, "model_route_resolver", None)
    resolve_fallbacks = getattr(resolver, "resolve_fallback_routes", None)
    if resolve_fallbacks is not None and route.fallback_profile_ids:
        fallback_routes = [
            r for r in list(await resolve_fallbacks(route)) if isinstance(r, ResolvedModelRoute)
        ]
        if fallback_routes:
            from apps.cosa.models.fallback_model import FallbackModel

            model_client = FallbackModel(
                model_client,
                primary_profile_id=route.profile_id,
                fallbacks=[
                    (r.profile_id, functools.partial(factory.create, r)) for r in fallback_routes
                ],
            )
            # Để record_route_usage ghi đúng provider/model của profile fallback.
            model_client.fallback_routes = fallback_routes

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
    return kernel, model_client


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
    route: ResolvedModelRoute | None = None
    model_client: Any = None
    if resolver is not None:
        route = await bind_route_to_run(resolver, prep.req, prep.spec)
        prep.req.model_policy = _route_provenance(route)
        await _enforce_usage_budget(plane, route, prep=prep)
        if not route.is_system_default:
            kernel, model_client = await _build_routed_kernel_with_model(plane, route)

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
    if route is not None:
        meta = getattr(prep.req, "metadata", None) or {}
        await record_route_usage(
            plane,
            route=route,
            model_client=model_client,
            result=run_result,
            run_id=run_id,
            workspace_id=workspace_id,
            project_id=meta.get("project_id"),
            agent_spec_id=getattr(prep.spec, "id", None),
            initiative_id=meta.get("initiative_id"),
        )
    return run_result, time.monotonic() - _start


async def _enforce_usage_budget(
    plane: CosaAgentPlane,
    route: ResolvedModelRoute,
    *,
    prep: RunCorePrep | None = None,
) -> None:
    """Quota token tháng của workspace + budget_usd_limit của profile, TRƯỚC khi
    dựng client (review 2026-09-27 G-3) + Initiative budget check (Task 5)."""
    from apps.cosa.models.usage import (
        UsageBudgetExceeded,
        check_initiative_budget,
        check_usage_budget,
        month_start,
    )

    budget: float | None = None
    repo = getattr(plane, "model_routing_repository", None)
    if not route.is_system_default and repo is not None:
        profile = await repo.get_profile(route.workspace_id, route.profile_id)
        budget = getattr(profile, "budget_usd_limit", None) if profile is not None else None
    try:
        await check_usage_budget(
            getattr(plane, "usage_ledger", None), route, profile_budget_usd=budget
        )
    except UsageBudgetExceeded as exc:
        logger.warning("usage budget blocked run: %s", exc.detail)
        raise RunCoreError("usage_budget_exceeded", compliance_code=exc.code) from exc

    if prep is not None:
        meta = getattr(prep.req, "metadata", None) or {}
        initiative_id = meta.get("initiative_id")
        project_id = meta.get("project_id")
        if initiative_id:
            if not project_id:
                raise RunCoreError(
                    "missing_project_scope", compliance_code="initiative_scope_mismatch"
                )
            budget_policy = meta.get("initiative_budget_policy") or meta.get("budget_policy")
            if budget_policy and isinstance(budget_policy, dict):
                soft = budget_policy.get("soft_cost_threshold")
                hard = budget_policy.get("hard_cost_threshold")
                period = budget_policy.get("period", "TOTAL")
                since = month_start() if period == "MONTHLY" else None
                try:
                    await check_initiative_budget(
                        getattr(plane, "usage_ledger", None),
                        workspace_id=route.workspace_id,
                        project_id=str(project_id),
                        initiative_id=str(initiative_id),
                        soft_budget_usd=soft,
                        hard_budget_usd=hard,
                        since=since,
                    )
                except UsageBudgetExceeded as exc:
                    logger.warning("initiative budget blocked run: %s", exc.detail)
                    raise RunCoreError("usage_budget_exceeded", compliance_code=exc.code) from exc


async def record_route_usage(
    plane: Any,
    *,
    route: ResolvedModelRoute,
    model_client: Any,
    result: Any,
    run_id: str,
    workspace_id: str,
    project_id: str | None,
    agent_spec_id: str | None,
    initiative_id: str | None = None,
) -> None:
    """Ghi 1 dòng usage theo profile THẬT đã phục vụ (fallback nếu có) + metric
    token theo model của route. Lỗi ghi không được làm hỏng run đã xong."""
    from apps.cosa.models.usage import UsageEntry, estimate_cost_usd, usage_from_result
    from apps.cosa.observability.metrics import record_model_tokens

    p_tok, c_tok = usage_from_result(result)
    served = route
    active = getattr(model_client, "active_profile_id", None)
    if isinstance(active, str) and active != route.profile_id:
        for r in getattr(model_client, "fallback_routes", []) or []:
            if r.profile_id == active:
                served = r
                break
    try:
        record_model_tokens(served.model_id, p_tok, c_tok)
    except Exception:
        logger.debug("record_model_tokens failed", exc_info=True)
    ledger = getattr(plane, "usage_ledger", None)
    if ledger is None or (p_tok == 0 and c_tok == 0):
        return
    try:
        await ledger.record(
            UsageEntry(
                workspace_id=workspace_id,
                project_id=str(project_id) if project_id else None,
                initiative_id=str(initiative_id) if initiative_id else None,
                run_id=run_id,
                agent_spec_id=agent_spec_id,
                profile_id=served.profile_id,
                provider_type=str(served.provider_type.value),
                model_id=served.model_id,
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
                cost_usd=estimate_cost_usd(served.provider_type, served.model_id, p_tok, c_tok),
            )
        )
    except Exception:
        logger.warning("usage ledger record failed run=%s", run_id, exc_info=True)


async def kernel_for_resume(
    plane: Any, *, workspace_id: str | None, run_id: str
) -> tuple[Any, ResolvedModelRoute | None, Any]:
    """Kernel cho resume cùng route với lúc chạy (trước đây resume luôn dùng
    `plane.kernel` = model mặc định hệ thống, bỏ qua profile của workspace).
    Không enforce ngân sách: resume là phần việc founder đã duyệt."""
    resolver = getattr(plane, "model_route_resolver", None)
    if resolver is None or not workspace_id:
        return plane.kernel, None, None
    run = await plane.repository.get_run(run_id)
    spec_id = getattr(run, "root_executable_id", None) if run is not None else None
    if not spec_id:
        return plane.kernel, None, None
    route = await resolver.resolve_route(workspace_id, spec_id)
    if route.is_system_default:
        return plane.kernel, route, None
    kernel, model_client = await _build_routed_kernel_with_model(plane, route)
    return kernel, route, model_client
