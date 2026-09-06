from __future__ import annotations

import inspect
import logging
import re
from typing import Any

import httpx
from agent.artifacts import WorkspaceArtifact
from agent.capabilities.gateway import GatewayExecutionRequest
from agent.contracts.run import RunRequest

from apps.cosa.agents.registry_loader import load_registered_agent_spec
from apps.cosa.agents.specs import COSA_CUSTOMER_SUPPORT_AGENT_SPEC
from apps.cosa.api.event_stream import CosaEventStreamManager, redact_ux_event_payload
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.config.service_identity import require_internal_url, require_service_token

logger = logging.getLogger(__name__)

__all__ = ["callback_company_result", "run_customer_support_copilot"]

FORBIDDEN_CAP_RE = re.compile(
    r"(\.write$|\.send$|\.execute$|message\.send|assignment\.write|lead\.write|opportunity\.write)"
)


async def _execute_via_gateway(
    plane: Any,
    capability_id: str,
    input_payload: dict[str, Any],
    ctx: dict[str, Any],
    *,
    run_id: str,
    workspace_id: str,
    principal: str,
    correlation_id: str,
    stream_repo: Any,
    stream_mgr: CosaEventStreamManager,
) -> Any:
    """Thực thi 1 capability qua CapabilityGateway thật (idempotency/
    governance/audit/connector-grant verify) — IA25 phần 2: trước đây
    Copilot gọi `plane.capability_registry.get_handler(...)` rồi CALL
    HANDLER TRỰC TIẾP, bỏ qua HOÀN TOÀN pipeline gateway mà mọi capability
    khác trong hệ thống đều phải đi qua (không audit event, không
    idempotency claim, không re-verify connector grant, không approval
    gate). `plane.gateway` là CÙNG MỘT CapabilityGateway instance đã được
    compose sẵn cho luồng tool-call bình thường (xem agent_plane.py) — dùng
    lại, không tạo pipeline governance thứ hai.

    Trả `None` (và đã emit run.failed + callback company failed) nếu gateway
    không hoàn thành (denied/failed/waiting_approval/in_progress) — caller
    phải `if result is None: return` ngay, không tiếp tục dùng output rỗng.
    """
    req = GatewayExecutionRequest(
        run_id=run_id,
        capability_id=capability_id,
        input_payload=input_payload,
        principal=principal,
        workspace_id=workspace_id,
        context=dict(ctx),
    )
    result = await plane.gateway.execute(req)

    if result.status == "completed":
        return result.output_payload

    reason_code = f"capability_gateway_{result.status}"
    logger.error(
        "Copilot run %s: capability %s did not complete via gateway (status=%s, error=%s)",
        run_id,
        capability_id,
        result.status,
        result.error_message,
    )
    if stream_repo:
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id="",
            event_type="run.failed",
            payload={
                "error": result.error_message or f"capability {capability_id} not completed",
                "reason_code": reason_code,
                "capability": capability_id,
            },
            correlation_id=correlation_id,
        )
    await callback_company_result(run_id, "failed", reason_code=reason_code)
    return None


async def callback_company_result(
    run_id: str,
    status: str,
    artifact_ref: str | None = None,
    summary_ref: str | None = None,
    reason_code: str | None = None,
    evidence_refs: list[str] | None = None,
) -> None:
    company_base_url = require_internal_url(
        "COMPANY_SERVICE_URL", purpose="copilot callback", default_dev="http://127.0.0.1:4000"
    )
    service_token = require_service_token("COSA_SERVICE_TOKEN", purpose="copilot callback")

    url = f"{company_base_url}/commercial/engagement/copilot-invocations/{run_id}/result"
    headers = {
        "Content-Type": "application/json",
        "X-Cosa-Service-Token": service_token,
    }
    body: dict[str, Any] = {
        "runId": run_id,
        "status": status,
        "artifactRef": artifact_ref,
        "summaryRef": summary_ref,
        "reasonCode": reason_code,
        "evidenceRefs": evidence_refs or [],
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code >= 400:
                logger.warning(
                    "Failed to callback company service result for run %s: status %s",
                    run_id,
                    resp.status_code,
                )
    except Exception as e:
        logger.warning("Exception during callback company service for run %s: %s", run_id, e)


async def run_customer_support_copilot(
    plane: CosaAgentPlane,
    stream_mgr: CosaEventStreamManager,
    payload: dict[str, Any],
) -> None:
    run_id = payload["run_id"]
    workspace_id = payload["workspace_id"]
    correlation_id = payload.get("correlation_id", "")
    stream_repo = getattr(plane, "run_stream_event_repository", None)

    # 1. Guard (defense in depth): check spec capabilities
    spec = COSA_CUSTOMER_SUPPORT_AGENT_SPEC
    if getattr(plane, "spec_registry", None):
        fetched_spec, spec_reason = await load_registered_agent_spec(
            plane.spec_registry,
            COSA_CUSTOMER_SUPPORT_AGENT_SPEC.id,
            version=COSA_CUSTOMER_SUPPORT_AGENT_SPEC.version,
        )
        if fetched_spec is None:
            reason = spec_reason or "agent_spec_resolution_failed"
            logger.error(
                "Registered copilot spec %s unavailable; failing closed (reason=%s)",
                COSA_CUSTOMER_SUPPORT_AGENT_SPEC.id,
                reason,
            )
            if stream_repo:
                await stream_mgr.emit(
                    stream_repo,
                    run_id=run_id,
                    conversation_id="",
                    event_type="run.failed",
                    payload={
                        "error": f"registered copilot spec unavailable: {reason}",
                        "reason_code": reason,
                    },
                    correlation_id=correlation_id,
                )
            await callback_company_result(run_id, "failed", reason_code=reason)
            return
        spec = fetched_spec

    for cap in spec.capability_refs:
        if FORBIDDEN_CAP_RE.search(cap):
            logger.error("Spec %s holds forbidden write/send capability: %s", spec.id, cap)
            if stream_repo:
                await stream_mgr.emit(
                    stream_repo,
                    run_id=run_id,
                    conversation_id="",
                    event_type="run.failed",
                    payload={"error": f"forbidden capability in copilot spec: {cap}"},
                    correlation_id=correlation_id,
                )
            await callback_company_result(run_id, "failed", reason_code="forbidden_capability")
            return

    # IA25: delegation_token PHẢI do services/company mint sẵn cho đúng
    # người dùng thật đã yêu cầu Copilot (mintCopilotDelegationToken —
    # copilot_routes.py bắt buộc field này ở request). Trước đây thiếu
    # field này thì tự mint bằng mint_company_delegation() dưới actor giả
    # "0" khi không rõ actor_id/user_id — nhưng mint_company_delegation() ký
    # theo hình dạng "company delegation" (aud=company, COSA_COMPANY_
    # DELEGATION_SECRET) trong khi các route Copilot thực sự gọi
    # (/commercial/engagement/threads/:id/context v.v.) xác thực bằng
    # verifyAccessToken (phiên đăng nhập local, JWT_SECRET) — token tự mint
    # ở đây LUÔN sai định dạng cho đích đến thật, không phải một fallback có
    # tác dụng. Fail-closed thay vì mint một token chắc chắn không dùng được.
    delegation_token = payload.get("delegation_token")
    if not delegation_token:
        logger.error(
            "run_id=%s missing delegation_token in copilot payload, failing closed", run_id
        )
        if stream_repo:
            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id="",
                event_type="run.failed",
                payload={"error": "missing_delegation_token"},
                correlation_id=correlation_id,
            )
        await callback_company_result(run_id, "failed", reason_code="missing_delegation_token")
        return

    try:
        ctx = {
            "workspace_id": workspace_id,
            "run_id": run_id,
            "delegation_token": delegation_token,
            "token": delegation_token,
        }

        # 3. Assemble minimized read context via gateway
        thread_ref = payload.get("thread_ref", {})
        thread_id = thread_ref.get("thread_id")
        contact_id = thread_ref.get("contact_id")
        identity_verified = payload.get("identity_verified", False)
        knowledge_scope = payload.get("knowledge_scope", {})

        principal = payload.get("principal", "system:copilot")

        thread_context = {}
        if thread_id:
            thread_context = await _execute_via_gateway(
                plane,
                "engagement.thread.read",
                {"thread_id": thread_id},
                ctx,
                run_id=run_id,
                workspace_id=workspace_id,
                principal=principal,
                correlation_id=correlation_id,
                stream_repo=stream_repo,
                stream_mgr=stream_mgr,
            )
            if thread_context is None:
                return

        customer_360 = {}
        if contact_id:
            customer_360 = await _execute_via_gateway(
                plane,
                "commercial.customer_360.read",
                {"contact_id": contact_id, "identity_verified": identity_verified},
                ctx,
                run_id=run_id,
                workspace_id=workspace_id,
                principal=principal,
                correlation_id=correlation_id,
                stream_repo=stream_repo,
                stream_mgr=stream_mgr,
            )
            if customer_360 is None:
                return

        knowledge_profile = {}
        if knowledge_scope:
            knowledge_profile = await _execute_via_gateway(
                plane,
                "knowledge.profile.read",
                knowledge_scope,
                ctx,
                run_id=run_id,
                workspace_id=workspace_id,
                principal=principal,
                correlation_id=correlation_id,
                stream_repo=stream_repo,
                stream_mgr=stream_mgr,
            )
            if knowledge_profile is None:
                return

        # 4. Build Model Input
        context_bundle = {
            "thread_context": thread_context,
            "customer_360": customer_360,
            "knowledge_profile": knowledge_profile,
            "intent": payload.get("intent", "summarize"),
            "identity_verified": identity_verified,
        }

        user_prompt = (
            f"Hãy phân tích thread {thread_id} với intent '{payload.get('intent', 'summarize')}'. "
            f"Khách hàng identity_verified={identity_verified}. "
            "Tạo artifact tóm tắt, trích xuất căn cứ, và bản nháp phản hồi đề xuất."
        )

        run_req = RunRequest(
            run_id=run_id,
            principal=payload.get("principal", "system:copilot"),
            root_executable_ref=spec.to_pinned_identity()
            if hasattr(spec, "to_pinned_identity")
            else str(spec.id),
            input={"prompt": user_prompt, "context": context_bundle},
            workspace_id=workspace_id,
            correlation_id=correlation_id,
        )

        if hasattr(plane.kernel, "run"):
            kernel_resp = await plane.kernel.run(run_req, spec)
        elif hasattr(plane.kernel, "execute_run"):
            kernel_resp = await plane.kernel.execute_run(run_req)
        else:
            raise RuntimeError("Kernel does not support run or execute_run")

        kernel_status = getattr(kernel_resp, "status", None) or "COMPLETED"
        final_out = getattr(kernel_resp, "final_output", None)
        if final_out is None and hasattr(kernel_resp, "output"):
            final_out = kernel_resp.output

        # Validate Output: DO NOT use empty final_output as success
        output_valid = bool(
            final_out
            and isinstance(final_out, dict)
            and (final_out.get("summary") or final_out.get("recommended_response_draft"))
        )

        output_data = final_out if isinstance(final_out, dict) else {}
        summary = output_data.get("summary", "")
        draft_body = output_data.get("recommended_response_draft", "")
        intent = output_data.get("intent") or payload.get("intent", "summarize")
        missing_info = output_data.get("missing_info") or []
        sales_signal = output_data.get("sales_signal") or "None"
        evidence_refs = output_data.get("evidence_refs") or ["thread.context"]

        artifact_persisted = False
        artifact_ref = f"art_{run_id}"
        summary_ref = f"sum_{run_id}"

        if output_valid:
            draft_result = await _execute_via_gateway(
                plane,
                "engagement.message.draft",
                {
                    "thread_id": str(thread_id),
                    "draft_body": str(draft_body),
                    "evidence_refs": evidence_refs,
                    "rationale": str(summary),
                },
                ctx,
                run_id=run_id,
                workspace_id=workspace_id,
                principal=payload.get("principal", "system:copilot"),
                correlation_id=correlation_id,
                stream_repo=stream_repo,
                stream_mgr=stream_mgr,
            )
            if draft_result is None:
                return

            # 5. Persist Artifact & verify readable
            if plane.artifact_repository is not None:
                try:
                    artifact = WorkspaceArtifact(
                        artifact_id=artifact_ref,
                        workspace_id=workspace_id,
                        conversation_id=str(thread_id or "copilot"),
                        run_id=run_id,
                        artifact_kind="assistant_output",
                        display_name="Customer Support Copilot Draft",
                        media_type="application/json",
                        object_ref=f"artifact://copilot/{run_id}/draft",
                    )
                    await plane.artifact_repository.create(artifact)
                    if hasattr(plane.artifact_repository, "get"):
                        # IA06: ArtifactRepository.get() nhận (workspace_id,
                        # artifact_id) — trước đây chỉ truyền artifact_ref
                        # (1 arg), khiến repository thật (InMemory/Postgres)
                        # raise TypeError, bị nuốt bởi except bên dưới và báo
                        # artifact_persisted=False cho một artifact thực ra ĐÃ
                        # được create() thành công phía trên — output hợp lệ
                        # bị báo thất bại oan.
                        get_fn = plane.artifact_repository.get
                        if (
                            inspect.iscoroutinefunction(get_fn)
                            or type(get_fn).__name__ == "AsyncMock"
                        ):
                            retrieved = await get_fn(workspace_id, artifact_ref)
                            artifact_persisted = retrieved is not None
                        elif callable(get_fn):
                            res = get_fn(workspace_id, artifact_ref)
                            resolved_artifact = await res if inspect.isawaitable(res) else res
                            artifact_persisted = resolved_artifact is not None
                        else:
                            # Có thuộc tính "get" nhưng không callable — không
                            # thể xác minh đã persist, fail-closed.
                            artifact_persisted = False
                    else:
                        # Repository không có get() để verify — fail-closed,
                        # không suy diễn "chắc là đã lưu".
                        artifact_persisted = False
                except Exception as e:
                    logger.warning("Failed to persist copilot artifact: %s", e)
                    artifact_persisted = False
            else:
                # IA06: KHÔNG có artifact_repository nào được cấu hình — không
                # có nơi nào lưu artifact, phải fail-closed (False), không
                # phải mặc định True như trước (khiến run được coi là hoàn
                # thành dù artifact chưa từng được ghi ở đâu cả).
                artifact_persisted = False

        from apps.cosa.worker.run_outcome import normalize_status, resolve_run_outcome

        outcome = resolve_run_outcome(
            status=kernel_status,
            output_valid=output_valid,
            artifact_persisted=artifact_persisted,
        )

        if outcome == "completed":
            if stream_repo:
                ux_payload = {
                    "run_id": run_id,
                    "status": "completed",
                    "artifact_ref": artifact_ref,
                    "summary_ref": summary_ref,
                    "summary": summary,
                    "recommended_response_draft": draft_body,
                    "intent": intent,
                    "missing_info": missing_info,
                    "sales_signal": sales_signal,
                    "evidence_refs": evidence_refs,
                }
                redacted = redact_ux_event_payload("run.completed", ux_payload)
                await stream_mgr.emit(
                    stream_repo,
                    run_id=run_id,
                    conversation_id="",
                    event_type="run.completed",
                    payload=redacted,
                    correlation_id=correlation_id,
                )
            await callback_company_result(
                run_id,
                "completed",
                artifact_ref=artifact_ref,
                summary_ref=summary_ref,
                evidence_refs=evidence_refs,
            )
        else:
            reason = (
                "kernel_failed"
                if normalize_status(kernel_status) in ("FAILED", "FAIL")
                else "invalid_output"
                if not output_valid
                else "missing_artifact"
                if not artifact_persisted
                else "run_failed"
            )
            if stream_repo:
                await stream_mgr.emit(
                    stream_repo,
                    run_id=run_id,
                    conversation_id="",
                    event_type=f"run.{outcome}",
                    payload={"error": f"run_{outcome}", "reason_code": reason},
                    correlation_id=correlation_id,
                )
            await callback_company_result(
                run_id,
                outcome,
                reason_code=reason,
            )

    except Exception:
        logger.exception("Copilot run %s crashed", run_id)
        if stream_repo:
            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id="",
                event_type="run.failed",
                payload={"error": "internal_error", "reason_code": "copilot_unhandled_exception"},
                correlation_id=correlation_id,
            )
        await callback_company_result(run_id, "failed", reason_code="copilot_unhandled_exception")
        return
