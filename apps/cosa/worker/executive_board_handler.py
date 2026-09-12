from __future__ import annotations

import logging
from typing import Any

from agent.executive_board.models import (
    EvidenceRef,
    ExecutiveAnalysisOutcome,
    ExecutiveAnalysisRequest,
    ExecutiveBoardInputError,
    RolePin,
)
from agent.executive_board.runner import ExecutiveBoardRunner

from apps.cosa.company.executive_board_client import (
    ExecutiveBoardClient,
    ExecutiveBoardClientError,
)

logger = logging.getLogger(__name__)

__all__ = [
    "execute_executive_deliberation_framed_task",
]


async def execute_executive_deliberation_framed_task(
    plane: Any,
    stream_mgr: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Worker task xử lý event executive.deliberation.framed.v1.

    Quy trình:
    1. Kiểm tra payload (workspace_id, project_id, deliberation_id, frame_version, role_pins).
    2. Khởi tạo ExecutiveBoardRunner với model / resolver cô lập (không peer drafts).
    3. Thực thi phân tích độc lập cho từng vai trò đã pin trong frame.
    4. Gửi kết quả (thành công hoặc thất bại) qua ExecutiveBoardClient về Company internal callback.
    """
    workspace_id = payload.get("workspace_id")
    project_id = payload.get("project_id")
    deliberation_id = payload.get("deliberation_id")
    frame_version = payload.get("frame_version") or 1
    role_pins = payload.get("role_pins") or []

    if not workspace_id or not project_id or not deliberation_id:
        raise ValueError("Missing required fields (workspace_id, project_id, deliberation_id)")

    if not role_pins:
        logger.warning(
            "deliberation_id=%s has no role_pins in framed event, nothing to analyze",
            deliberation_id,
        )
        return {"status": "completed", "analyzed_roles": 0}

    client = getattr(plane, "executive_board_client", None) or ExecutiveBoardClient()
    runner = getattr(plane, "executive_board_runner", None) or ExecutiveBoardRunner(
        kernel=plane.kernel,
        spec_registry=plane.spec_registry,
    )


    raw_evidence = payload.get("evidence_refs") or []
    evidence_refs = tuple(
        EvidenceRef(
            source_ref=ev.get("source_ref", ev.get("id", "")),
            source_hash=ev.get("source_hash", ev.get("hash", "")),
            classification=ev.get("classification", "internal"),
            project_id=ev.get("project_id") or project_id,
        )
        for ev in raw_evidence
        if isinstance(ev, dict)
    )

    question = (
        payload.get("problem_statement")
        or payload.get("title")
        or payload.get("question")
        or "Executive Deliberation Analysis"
    )

    results: list[dict[str, Any]] = []

    for pin_data in role_pins:
        role_key = pin_data.get("role_key")
        if not role_key:
            continue

        role_pin = RolePin(
            role_key=role_key,
            assignment_id=pin_data.get("assignment_id", f"assign-{role_key}"),
            spec_id=pin_data.get("spec_id", f"cosa.agents.executive.{role_key}"),
            spec_version=pin_data.get("spec_version", "1.0.0"),
            spec_hash=pin_data.get("spec_hash", "valid_hash"),
            skill_pins=tuple(pin_data.get("skill_pins", ())),
        )

        request = ExecutiveAnalysisRequest(
            workspace_id=str(workspace_id),
            project_id=str(project_id),
            deliberation_id=str(deliberation_id),
            frame_version=int(frame_version),
            role_key=str(role_key),
            question=str(question),
            role_pin=role_pin,
            evidence_refs=evidence_refs,
            peer_drafts=None,  # Bắt buộc None: không lộ bản nháp của role khác
            mock_model_output=payload.get("mock_model_output"),
        )

        try:
            outcome: ExecutiveAnalysisOutcome = await runner.run(request)
        except ExecutiveBoardInputError as exc:
            logger.error("deliberation_id=%s role=%s input validation failed: %s", deliberation_id, role_key, exc)
            outcome = ExecutiveAnalysisOutcome(
                kind="executive.analysis.failed.v1",
                deliberation_id=str(deliberation_id),
                frame_version=int(frame_version),
                role_key=str(role_key),
                error_detail=str(exc),
            )
        except Exception as exc:
            logger.exception("deliberation_id=%s role=%s unexpected error: %s", deliberation_id, role_key, exc)
            outcome = ExecutiveAnalysisOutcome(
                kind="executive.analysis.failed.v1",
                deliberation_id=str(deliberation_id),
                frame_version=int(frame_version),
                role_key=str(role_key),
                error_detail=f"Unexpected error: {exc}",
            )

        # Gửi callback về Company internal endpoint
        callback_payload = outcome.model_dump(mode="json")
        try:
            await client.submit_analysis_callback(
                workspace_id=str(workspace_id),
                project_id=str(project_id),
                deliberation_id=str(deliberation_id),
                payload=callback_payload,
            )
            results.append({"role_key": role_key, "outcome": outcome.kind})
        except ExecutiveBoardClientError as exc:
            logger.error(
                "deliberation_id=%s role=%s callback submission failed: %s",
                deliberation_id,
                role_key,
                exc,
            )
            results.append({"role_key": role_key, "outcome": "CALLBACK_FAILED", "error": str(exc)})

    return {"status": "completed", "results": results}
