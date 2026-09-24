from __future__ import annotations

import logging
from typing import Any

from agent.executive_board.models import (
    AdvisorOverlayPin,
    EvidenceRef,
    ExecutiveAnalysisOutcome,
    ExecutiveAnalysisRequest,
    ExecutiveBoardInputError,
    PinnedSkillIdentity,
    ProjectDeploymentPin,
    SelectedAdvisorExecutionPin,
)

from apps.cosa.company.executive_board_client import (
    ExecutiveBoardAuthorityError,
    ExecutiveBoardClient,
    ExecutiveBoardClientError,
)
from apps.cosa.worker.executive_board_runtime import build_executive_board_runner

logger = logging.getLogger(__name__)

__all__ = [
    "ExecutiveBoardPayloadError",
    "execute_executive_deliberation_framed_task",
    "parse_selected_advisor_pin",
]


class ExecutiveBoardPayloadError(ValueError):
    """Payload framed event hỏng/thiếu pin — fail có cấu trúc, không tự điền giá trị mặc định."""


def _required(raw: dict[str, Any], key: str, where: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ExecutiveBoardPayloadError(f"{where}: missing or invalid '{key}'")
    return value


def parse_selected_advisor_pin(raw: Any) -> SelectedAdvisorExecutionPin:
    """Parse 1 phần tử `selectedRoles` đúng như Company phát (camelCase). Không có default
    cho spec id/version/hash: thiếu là lỗi payload, để worker không chạy nhầm định danh."""
    if not isinstance(raw, dict):
        raise ExecutiveBoardPayloadError("selected role pin is not an object")
    role_key = _required(raw, "roleKey", "selected role pin")
    deployment = raw.get("deployment")
    overlay = raw.get("overlay")
    if not isinstance(deployment, dict) or not isinstance(overlay, dict):
        raise ExecutiveBoardPayloadError(f"{role_key}: deployment and overlay pins are required")
    where = f"{role_key}.deployment"
    dep = ProjectDeploymentPin(
        project_agent_deployment_id=_required(deployment, "projectAgentDeploymentId", where),
        profile_key=_required(deployment, "profileKey", where),
        spec_id=_required(deployment, "specId", where),
        spec_version=_required(deployment, "specVersion", where),
        spec_hash=_required(deployment, "specHash", where),
    )
    where = f"{role_key}.overlay"
    skills = overlay.get("skillPins")
    if not isinstance(skills, list) or not skills:
        raise ExecutiveBoardPayloadError(f"{where}: skillPins are required")
    ovl = AdvisorOverlayPin(
        role_key=_required(overlay, "roleKey", where),
        overlay_spec_id=_required(overlay, "overlaySpecId", where),
        overlay_spec_version=_required(overlay, "overlaySpecVersion", where),
        overlay_spec_hash=_required(overlay, "overlaySpecHash", where),
        skill_pins=tuple(
            PinnedSkillIdentity(
                skill_id=_required(sk, "skillId", where),
                version=_required(sk, "version", where),
                definition_hash=_required(sk, "definitionHash", where),
            )
            for sk in skills
            if isinstance(sk, dict)
        ),
    )
    if ovl.role_key != role_key or len(ovl.skill_pins) != len(skills):
        raise ExecutiveBoardPayloadError(f"{role_key}: overlay pin does not match role")
    return SelectedAdvisorExecutionPin(role_key=role_key, deployment=dep, overlay=ovl)


def _failed_outcome(
    pin: SelectedAdvisorExecutionPin, deliberation_id: str, frame_version: int, detail: str
) -> ExecutiveAnalysisOutcome:
    # Outcome thất bại vẫn mang hash pin, nếu không Company sẽ từ chối callback và
    # deliberation kẹt ở ANALYZING mà không có dấu vết lỗi.
    return ExecutiveAnalysisOutcome(
        kind="executive.analysis.failed.v1",
        deliberation_id=deliberation_id,
        frame_version=frame_version,
        role_key=pin.role_key,
        error_detail=detail,
        deployment_pin_hash=pin.deployment.identity_hash(),
        overlay_pin_hash=pin.overlay.identity_hash(),
    )


def _authority_pin_matches(rol_pin: Any, pin: SelectedAdvisorExecutionPin) -> bool:
    """Pin Company trả về từ authority endpoint phải bằng đúng pin worker sắp thực thi."""
    if not isinstance(rol_pin, dict):
        return False
    try:
        live = parse_selected_advisor_pin(rol_pin)
    except ExecutiveBoardPayloadError:
        return False
    return live == pin


async def _analyze_role(
    client: Any,
    runner: Any,
    request: ExecutiveAnalysisRequest,
    pin: SelectedAdvisorExecutionPin,
    workspace_id: Any,
    project_id: Any,
) -> ExecutiveAnalysisOutcome:
    deliberation_id = request.deliberation_id
    frame_version = request.frame_version
    role_key = request.role_key

    # Company re-check quyền ngay trước khi chạy (office + Project deployment + stage +
    # pin còn đúng): deployment bị pause/đổi sau frame thì không có model call nào.
    try:
        authority = await client.get_deliberation_authority(
            workspace_id=str(workspace_id),
            project_id=str(project_id),
            deliberation_id=deliberation_id,
            role_key=role_key,
            frame_version=frame_version,
        )
    except ExecutiveBoardAuthorityError as exc:
        return _failed_outcome(pin, deliberation_id, frame_version, f"AUTHORITY_DENIED: {exc}")
    except ExecutiveBoardClientError as exc:
        return _failed_outcome(pin, deliberation_id, frame_version, f"AUTHORITY_UNAVAILABLE: {exc}")
    if not _authority_pin_matches(authority.get("rolePin"), pin):
        return _failed_outcome(
            pin,
            deliberation_id,
            frame_version,
            "PIN_DRIFT: Company authority pin differs from the pin in the framed event",
        )

    try:
        outcome: ExecutiveAnalysisOutcome = await runner.run(request)
        return outcome
    except ExecutiveBoardInputError as exc:
        logger.error(
            "deliberation_id=%s role=%s input validation failed: %s",
            deliberation_id,
            role_key,
            exc,
        )
        return _failed_outcome(pin, deliberation_id, frame_version, str(exc))
    except Exception as exc:
        logger.exception(
            "deliberation_id=%s role=%s unexpected error: %s", deliberation_id, role_key, exc
        )
        return _failed_outcome(pin, deliberation_id, frame_version, f"Unexpected error: {exc}")


async def execute_executive_deliberation_framed_task(
    plane: Any,
    stream_mgr: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Worker task xử lý event executive.deliberation.framed.v1.

    Quy trình:
    1. Kiểm tra payload (workspace_id, project_id, deliberation_id, frame_version, selected_roles).
    2. Khởi tạo ExecutiveBoardRunner với model / resolver cô lập (không peer drafts).
    3. Thực thi phân tích độc lập cho từng vai trò đã pin trong frame.
    4. Gửi kết quả (thành công hoặc thất bại) qua ExecutiveBoardClient về Company internal callback.
    """
    workspace_id = payload.get("workspace_id")
    project_id = payload.get("project_id")
    deliberation_id = payload.get("deliberation_id")
    frame_version = payload.get("frame_version") or 1
    selected_roles = payload.get("selected_roles") or []

    if not workspace_id or not project_id or not deliberation_id:
        raise ValueError("Missing required fields (workspace_id, project_id, deliberation_id)")

    if not selected_roles:
        logger.warning(
            "deliberation_id=%s has no selected_roles in framed event, nothing to analyze",
            deliberation_id,
        )
        return {"status": "completed", "analyzed_roles": 0}

    # Parse toàn bộ pin TRƯỚC khi chạy bất kỳ role nào: payload hỏng thì dừng cả event.
    pins = [parse_selected_advisor_pin(raw) for raw in selected_roles]

    client = getattr(plane, "executive_board_client", None) or ExecutiveBoardClient()
    runner = getattr(plane, "executive_board_runner", None) or build_executive_board_runner(plane)

    raw_evidence = payload.get("evidence_refs") or []
    evidence_refs = tuple(
        EvidenceRef(
            source_ref=str(ev.get("source_ref") or ev.get("id") or ""),
            source_hash=str(ev.get("source_hash") or ev.get("hash") or ""),
            classification=str(ev.get("classification") or "internal"),
            project_id=str(ev.get("project_id") or project_id),
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

    for execution_pin in pins:
        role_key = execution_pin.role_key

        request = ExecutiveAnalysisRequest(
            workspace_id=str(workspace_id),
            project_id=str(project_id),
            deliberation_id=str(deliberation_id),
            frame_version=int(frame_version),
            role_key=role_key,
            question=str(question),
            execution_pin=execution_pin,
            evidence_refs=evidence_refs,
            peer_drafts=None,  # Bắt buộc None: không lộ bản nháp của role khác
        )

        outcome = await _analyze_role(
            client, runner, request, execution_pin, workspace_id, project_id
        )

        # Gửi callback về Company internal endpoint
        # exclude_none: Encore từ chối `null` cho field optional (descriptor/error_detail...).
        callback_payload = outcome.model_dump(mode="json", exclude_none=True)
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
