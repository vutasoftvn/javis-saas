from __future__ import annotations

import asyncio
import inspect
import logging
import re
from typing import Any

import httpx
from agent.artifacts import WorkspaceArtifact
from agent.capabilities.registry import CapabilityHandler
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


async def _require_handler(
    plane: Any,
    capability_id: str,
    *,
    run_id: str,
    correlation_id: str,
    stream_repo: Any,
    stream_mgr: CosaEventStreamManager,
) -> CapabilityHandler | None:
    """Trả handler hoặc None. Nếu None: emit run.failed có reason_code
    và callback Company failed — caller phải return ngay."""
    handler = plane.capability_registry.get_handler(capability_id)
    if handler is not None:
        return handler
    logger.error("Copilot run %s: capability not registered: %s", run_id, capability_id)
    if stream_repo:
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id="",
            event_type="run.failed",
            payload={
                "error": f"capability not registered: {capability_id}",
                "reason_code": "capability_not_registered",
                "capability": capability_id,
            },
            correlation_id=correlation_id,
        )
    await callback_company_result(run_id, "failed")
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

    try:
        # 2. Resolve principal / delegation token BEFORE context prefetch
        delegation_token = payload.get("delegation_token")
        if not delegation_token:
            from apps.cosa.auth.jwt import mint_company_delegation
            sub = str(payload.get("actor_id") or payload.get("user_id") or "0")
            delegation_token = mint_company_delegation(
                sub=sub,
                workspace_id=workspace_id,
                run_id=run_id,
                capability_ids=spec.capability_refs,
            )

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

        thread_context = {}
        if thread_id:
            thread_handler = await _require_handler(
                plane,
                "engagement.thread.read",
                run_id=run_id,
                correlation_id=correlation_id,
                stream_repo=stream_repo,
                stream_mgr=stream_mgr,
            )
            if thread_handler is None:
                return
            thread_context = await thread_handler({"thread_id": thread_id}, ctx)

        customer_360 = {}
        if contact_id:
            customer_handler = await _require_handler(
                plane,
                "commercial.customer_360.read",
                run_id=run_id,
                correlation_id=correlation_id,
                stream_repo=stream_repo,
                stream_mgr=stream_mgr,
            )
            if customer_handler is None:
                return
            customer_360 = await customer_handler(
                {"contact_id": contact_id, "identity_verified": identity_verified}, ctx
            )

        knowledge_profile = {}
        if knowledge_scope:
            knowledge_handler = await _require_handler(
                plane,
                "knowledge.profile.read",
                run_id=run_id,
                correlation_id=correlation_id,
                stream_repo=stream_repo,
                stream_mgr=stream_mgr,
            )
            if knowledge_handler is None:
                return
            knowledge_profile = await knowledge_handler(knowledge_scope, ctx)

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
            draft_handler = await _require_handler(
                plane,
                "engagement.message.draft",
                run_id=run_id,
                correlation_id=correlation_id,
                stream_repo=stream_repo,
                stream_mgr=stream_mgr,
            )
            if draft_handler is None:
                return
            await draft_handler(
                {
                    "thread_id": str(thread_id),
                    "draft_body": str(draft_body),
                    "evidence_refs": evidence_refs,
                    "rationale": str(summary),
                },
                ctx,
            )

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
                        if inspect.iscoroutinefunction(get_fn) or type(get_fn).__name__ == "AsyncMock":
                            retrieved = await get_fn(workspace_id, artifact_ref)
                            artifact_persisted = retrieved is not None
                        elif callable(get_fn):
                            res = get_fn(workspace_id, artifact_ref)
                            if inspect.isawaitable(res):
                                res = await res
                            artifact_persisted = res is not None
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
