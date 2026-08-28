from __future__ import annotations

import logging
import os
import re
from typing import Any
import httpx

from agent_core.artifacts import WorkspaceArtifact
from agent_core.contracts.run import RunRequest, RunStatus
from apps.cosa.agents.specs import COSA_CUSTOMER_SUPPORT_AGENT_SPEC
from apps.cosa.api.event_stream import CosaEventStreamManager, redact_ux_event_payload
from apps.cosa.composition.agent_plane import CosaAgentPlane

logger = logging.getLogger(__name__)

__all__ = ["callback_company_result", "run_customer_support_copilot"]

FORBIDDEN_CAP_RE = re.compile(
    r"(\.write$|\.send$|\.execute$|message\.send|assignment\.write|lead\.write|opportunity\.write)"
)


async def callback_company_result(
    run_id: str,
    status: str,
    artifact_ref: str | None = None,
    summary_ref: str | None = None,
) -> None:
    company_base_url = os.environ.get("COMPANY_SERVICE_URL", "http://127.0.0.1:4000")
    service_token = os.environ.get("COSA_SERVICE_TOKEN", "local-dev-service-token")

    url = f"{company_base_url}/commercial/engagement/copilot-invocations/{run_id}/result"
    headers = {
        "Content-Type": "application/json",
        "X-Cosa-Service-Token": service_token,
    }
    body = {
        "runId": run_id,
        "status": status,
        "artifactRef": artifact_ref,
        "summaryRef": summary_ref,
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
        try:
            fetched_spec = await plane.spec_registry.get_agent_spec(COSA_CUSTOMER_SUPPORT_AGENT_SPEC.id)
            if fetched_spec:
                spec = fetched_spec
        except Exception:
            pass

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
            await callback_company_result(run_id, "failed")
            return

    try:
        # 2. Assemble minimized read context
        thread_ref = payload.get("thread_ref", {})
        thread_id = thread_ref.get("thread_id")
        contact_id = thread_ref.get("contact_id")
        identity_verified = payload.get("identity_verified", False)
        knowledge_scope = payload.get("knowledge_scope", {})

        ctx = {"workspace_id": workspace_id, "run_id": run_id}

        thread_context = {}
        thread_handler = plane.capability_registry.get_handler("engagement.thread.read")
        if thread_handler and thread_id:
            thread_context = await thread_handler({"thread_id": thread_id}, ctx)

        customer_360 = {}
        customer_handler = plane.capability_registry.get_handler("commercial.customer_360.read")
        if customer_handler and contact_id:
            customer_360 = await customer_handler(
                {"contact_id": contact_id, "identity_verified": identity_verified}, ctx
            )

        knowledge_profile = {}
        knowledge_handler = plane.capability_registry.get_handler("knowledge.profile.read")
        if knowledge_handler and knowledge_scope:
            knowledge_profile = await knowledge_handler(knowledge_scope, ctx)

        # 3. Execute Kernel
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
            root_executable_ref=spec.to_pinned_identity() if hasattr(spec, "to_pinned_identity") else str(spec.id),
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

        final_out = getattr(kernel_resp, "final_output", None)
        if final_out is None and hasattr(kernel_resp, "output"):
            final_out = kernel_resp.output

        output_data = final_out if isinstance(final_out, dict) else {}
        summary = output_data.get("summary") or "Tóm tắt yêu cầu khách hàng"
        draft_body = (
            output_data.get("recommended_response_draft")
            or "Xin chào, cảm ơn bạn đã liên hệ. Chúng tôi đang kiểm tra thông tin."
        )
        intent = output_data.get("intent") or payload.get("intent", "summarize")
        missing_info = output_data.get("missing_info") or []
        sales_signal = output_data.get("sales_signal") or "None"
        evidence_refs = output_data.get("evidence_refs") or ["thread.context"]

        # Call draft capability handler to validate draft artifact
        draft_handler = plane.capability_registry.get_handler("engagement.message.draft")
        if draft_handler:
            await draft_handler(
                {
                    "thread_id": str(thread_id),
                    "draft_body": str(draft_body),
                    "evidence_refs": evidence_refs,
                    "rationale": str(summary),
                },
                ctx,
            )

        # 4. Persist Artifact
        artifact_ref = f"art_{run_id}"
        summary_ref = f"sum_{run_id}"

        if getattr(plane, "artifact_repository", None):
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
            except Exception as e:
                logger.warning("Failed to persist copilot artifact: %s", e)

        # 5. Emit UX SSE
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

        # 6. Callback Company Service
        await callback_company_result(
            run_id,
            "completed",
            artifact_ref=artifact_ref,
            summary_ref=summary_ref,
        )

    except Exception as e:
        logger.exception("Error executing customer support copilot run %s: %s", run_id, e)
        if stream_repo:
            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id="",
                event_type="run.failed",
                payload={"error": str(e)},
                correlation_id=correlation_id,
            )
        await callback_company_result(run_id, "failed")
