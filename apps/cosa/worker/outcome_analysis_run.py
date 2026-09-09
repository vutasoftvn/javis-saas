"""Worker path cho Outcome Analyst run (Task 4A).

Router phát `operating.task.result_submitted.v1` -> resolve binding
(resolve_outcome_analysis_binding) -> schedule task `outcome_analysis` với
snapshot employee/assignment/spec/skill đã pin. Worker này:

  * TỪ CHỐI payload thiếu request/result/binding hoặc capability vượt boundary
    6-item (spec §9.2);
  * chỉ được gọi sáu capability read + narrow record — KHÔNG task advance, KHÔNG
    KR write, KHÔNG external send, KHÔNG finance write;
  * ghi assessment qua endpoint Company hẹp `operations.outcome-assessment.record`
    kèm delegation scope {workspace_id, run_id, request_id, capability_ids}.

Việc chạy kernel thật để sinh expected-vs-actual + criterion scores nối tiếp
ở slice sau; hợp đồng attribution + capability boundary đã bất biến và có test.
"""

from __future__ import annotations

import logging
from typing import Any

from agent.workforce.outcome_analysis import OUTCOME_ANALYST_CAPABILITY_REFS

logger = logging.getLogger(__name__)

__all__ = ["OutcomeAnalysisPayloadError", "execute_outcome_analysis_run"]

_REQUIRED = (
    "request_id",
    "task_result_id",
    "contract_id",
    "workspace_id",
    "run_id",
    "agent_instance_id",
    "assignment_id",
    "skill_id",
    "skill_version",
    "definition_hash",
)

# Capability tuyệt đối cấm với Outcome Analyst (spec §9.2 Deny list).
_FORBIDDEN_CAPS = frozenset(
    {
        "operations.task.advance",
        "operations.task.create",
        "operations.project.stage.transition",
        "operations.kr.actual.write",
        "external.send",
    }
)


class OutcomeAnalysisPayloadError(ValueError):
    """Payload outcome-analysis không đủ hoặc capability vượt boundary."""


def validate_outcome_analysis_payload(payload: dict[str, Any]) -> tuple[str, ...]:
    missing = [k for k in _REQUIRED if not payload.get(k)]
    if missing:
        raise OutcomeAnalysisPayloadError(f"outcome analysis payload missing: {', '.join(missing)}")

    caps = tuple(str(c) for c in (payload.get("capability_refs") or []))
    if not caps:
        caps = tuple(sorted(OUTCOME_ANALYST_CAPABILITY_REFS))

    forbidden = [c for c in caps if c in _FORBIDDEN_CAPS]
    if forbidden:
        raise OutcomeAnalysisPayloadError(
            f"outcome analyst may not hold capabilities: {', '.join(forbidden)}"
        )
    extra = [c for c in caps if c not in OUTCOME_ANALYST_CAPABILITY_REFS]
    if extra:
        raise OutcomeAnalysisPayloadError(
            f"capability refs outside the Outcome Analyst boundary: {', '.join(extra)}"
        )
    return caps


async def execute_outcome_analysis_run(
    plane: Any,
    stream_mgr: Any,
    payload: dict[str, object],
) -> None:
    caps = validate_outcome_analysis_payload(payload)  # raises on bad payload/caps

    run_id = str(payload["run_id"])
    request_id = str(payload["request_id"])

    # Persist một run record tối thiểu carrying attribution employee/assignment
    # để investigation/scorecard truy ngược được.
    repo = getattr(plane, "repository", None)
    if repo is not None:
        from agent.runs.models import RunRecord, WorkforceRunAttribution

        existing = await repo.get_run(run_id)
        attribution = WorkforceRunAttribution(
            agent_instance_id=str(payload["agent_instance_id"]),
            assignment_id=str(payload["assignment_id"]),
            work_package_id=f"analysis:{request_id}",
            work_attempt_id=f"analysis-run:{run_id}",
        )
        if existing is None:
            await repo.create_run(
                RunRecord(
                    run_id=run_id,
                    workspace_id=str(payload["workspace_id"]),
                    principal=f"system:outcome-analyst:{payload['workspace_id']}",
                    root_executable_id=str(payload["skill_id"]),
                    workforce_attribution=attribution,
                )
            )
        else:
            await repo.attach_workforce_attribution(run_id, attribution)

    logger.info(
        "outcome analysis run scheduled: run_id=%s request_id=%s caps=%s",
        run_id,
        request_id,
        caps,
    )
    # NOTE: kernel execution + Company narrow-record call nối tiếp ở slice sau.
