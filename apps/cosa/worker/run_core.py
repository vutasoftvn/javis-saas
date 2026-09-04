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
from apps.cosa.observability.otel import trace_span

logger = logging.getLogger(__name__)

__all__ = [
    "RunCoreError",
    "RunCorePrep",
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

    req = RunRequest(
        run_id=run_id,
        principal=principal,
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": prompt},
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        metadata=run_metadata,
    )

    compliance_resolver = getattr(plane, "compliance_resolver", None)
    if compliance_resolver is None:
        raise RunCoreError("compliance_resolver_unavailable")

    try:
        compliance_metadata = await compliance_resolver.resolve_for_run(req, spec)
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
        extra_metadata=extra_metadata,
    )


async def run_kernel(
    plane: CosaAgentPlane,
    prep: RunCorePrep,
    *,
    workspace_id: str,
    run_id: str,
) -> tuple[Any, float]:
    """Gọi `plane.kernel.run` trong trace span; trả (run_result, duration_sec)."""
    _start = time.monotonic()
    async with trace_span(
        "kernel.run",
        attributes={
            "run_id": run_id,
            "agent_spec_id": getattr(prep.spec, "spec_id", None),
            "workspace_id": workspace_id,
        },
    ):
        run_result = await plane.kernel.run(prep.req, prep.spec)
    return run_result, time.monotonic() - _start
