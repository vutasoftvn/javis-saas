"""Verifier cho việc hoàn thành task WGA (Dự án B): chạy thẩm phán LLM và điều phối kiểm tra."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from agent.contracts.spec import AgentSpec
from agent.runs.models import RunStatus
from agent.verification.judge import JudgeOutputError, build_judge_prompt, parse_judge_output
from agent.verification.models import CriterionVerdict

from apps.cosa.agents.specs import COSA_VERIFIER_AGENT_SPEC
from apps.cosa.models.resolver import ModelRouteNotFound
from apps.cosa.policies.evaluator import READ_ONLY_RUN_KEY
from apps.cosa.worker.run_core import RunCoreError, prepare_run, run_kernel

logger = logging.getLogger(__name__)

_JUDGE_MAX_ATTEMPTS = 2


@dataclass(frozen=True)
class JudgeResult:
    verdicts: dict[str, tuple[CriterionVerdict, str]] | None
    verifier_run_id: str | None
    error: str | None


def _judge_text(run_result: Any) -> str:
    fo = run_result.final_output
    if isinstance(fo, dict):
        return str(fo.get("response", fo))
    return str(fo or "")


async def run_judge(
    plane: Any,
    *,
    producer_spec: AgentSpec,
    workspace_id: str,
    project_id: str,
    task_run_id: str,
    task_title: str,
    decision_reason: str,
    rubric_criteria: Sequence[dict[str, Any]],
    output_text: str,
) -> JudgeResult:
    """Chạy thẩm phán độc lập.

    Chuyển RunCoreError, ModelRouteNotFound, run thất bại/không hoàn tất và JSON sai thành
    JudgeResult(error=...). KHÔNG bắt lỗi hạ tầng bất ngờ (httpx, asyncpg, RuntimeError...): người gọi
    phải bọc (xem `verify_task_result`)."""
    expected = [
        str(c["id"])
        for c in rubric_criteria
        if isinstance(c, dict) and isinstance(c.get("id"), str) and c["id"].strip()
    ]
    base_prompt = build_judge_prompt(
        task_title=task_title,
        decision_reason=decision_reason,
        criteria=rubric_criteria,
        output_text=output_text,
    )
    compliance_spec = producer_spec.model_copy(
        update={
            "capability_refs": [],
            "model_input_capability_ref": producer_spec.model_input_capability_ref
            or COSA_VERIFIER_AGENT_SPEC.model_input_capability_ref,
        }
    )
    last_error = "judge_not_run"
    verifier_run_id: str | None = None
    for attempt in range(_JUDGE_MAX_ATTEMPTS):
        run_id = (
            f"{task_run_id}__verify" if attempt == 0 else f"{task_run_id}__verify_retry{attempt}"
        )
        prompt = (
            base_prompt
            if attempt == 0
            else (
                f"{base_prompt}\n\nYOUR PREVIOUS OUTPUT WAS REJECTED: {last_error[:200]}\n"
                "Return ONLY the JSON object, no prose, no markdown fences."
            )
        )
        verifier_run_id = run_id
        try:
            prep = await prepare_run(
                plane,
                run_id=run_id,
                local_spec=COSA_VERIFIER_AGENT_SPEC,
                prompt=prompt,
                principal=f"system:wga:{workspace_id}",
                workspace_id=workspace_id,
                conversation_id=f"wga_verify_{task_run_id}",
                policy_snapshot=None,
                extra_metadata={READ_ONLY_RUN_KEY: True},
                project_id=project_id,
                compliance_spec=compliance_spec,
            )
            run_result, _ = await run_kernel(plane, prep, workspace_id=workspace_id, run_id=run_id)
        except (RunCoreError, ModelRouteNotFound) as exc:
            reason = getattr(exc, "reason_code", None) or exc.__class__.__name__
            return JudgeResult(None, verifier_run_id, f"judge_run_failed:{reason}")
        if run_result.status != RunStatus.COMPLETED:
            return JudgeResult(None, verifier_run_id, f"judge_run_failed:{run_result.status}")
        try:
            return JudgeResult(
                parse_judge_output(_judge_text(run_result), expected), verifier_run_id, None
            )
        except JudgeOutputError as exc:
            last_error = str(exc)
    return JudgeResult(None, verifier_run_id, f"judge_output_invalid:{last_error}")
