"""Verifier cho việc hoàn thành task WGA (Dự án B): chạy thẩm phán LLM và điều phối kiểm tra."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from agent.contracts.done_criteria import DoneCriteriaError, parse_done_criteria
from agent.contracts.spec import AgentSpec
from agent.runs.models import RunEventRecord, RunStatus
from agent.verification.combine import combine
from agent.verification.deterministic import evaluate_deterministic
from agent.verification.judge import (
    JudgeOutputError,
    build_judge_prompt,
    clean_reason,
    parse_judge_output,
)
from agent.verification.models import (
    ArtifactFact,
    CriterionResult,
    CriterionVerdict,
    RunFacts,
    Verdict,
)
from agent.verification.repository import VerificationReport

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


_SUMMARY_MAX = 300
_REASON_MAX = 80


@dataclass(frozen=True)
class VerificationOutcome:
    verdict: Verdict
    report_id: str | None
    summary: str  # <= 300 ký tự, hiển thị cho founder
    results: list[CriterionResult]


def verification_enabled() -> bool:
    """Cờ đọc LÚC GỌI (không cache ở import)."""
    return os.environ.get("WGA_VERIFY_ON_COMPLETE") == "1"


def _valid_id(criterion: object) -> bool:
    return (
        isinstance(criterion, dict)
        and isinstance(criterion.get("id"), str)
        and bool(criterion["id"].strip())
    )


def _is_platform_evidence(artifact: Any, task_run_id: str) -> bool:
    """Artifact output tự động do `record_wga_task_evidence` tạo (khớp object_ref; nếu thiếu
    object_ref thì khớp kind=report + tên cố định)."""
    object_ref = getattr(artifact, "object_ref", None)
    if object_ref:
        return bool(object_ref == f"artifact://run/{task_run_id}/task-output")
    return (
        getattr(artifact, "artifact_kind", None) == "report"
        and getattr(artifact, "display_name", None) == "WGA task output"
    )


async def collect_run_facts(
    plane: Any, *, workspace_id: str, task_run_id: str, run_result: Any, output_text: str
) -> RunFacts:
    """Dữ kiện có thật của run để chấm tiêu chí tất định.

    `artifacts` chỉ gồm artifact do công cụ của agent tạo ra: artifact output tự động của nền tảng
    (`record_wga_task_evidence`, chạy TRƯỚC khi xác minh) KHÔNG BAO GIỜ được tính, nếu không
    `artifact_exists` luôn đạt."""
    final = getattr(run_result, "final_output", None)
    structured = final if isinstance(final, dict) and set(final) != {"response"} else None
    artifacts: list[ArtifactFact] = []
    repo = getattr(plane, "artifact_repository", None)
    if repo is not None:
        try:
            rows = await repo.list_for_conversation(workspace_id, f"wga_task_{task_run_id}")
            artifacts = [
                ArtifactFact(kind=str(a.artifact_kind), display_name=str(a.display_name))
                for a in rows
                if a.run_id == task_run_id
                and not _is_platform_evidence(a, task_run_id)
                and getattr(a, "archived_at", None) is None
                and getattr(a, "status", "available") != "archived"
            ]
        except Exception as exc:
            logger.warning(
                "verify: listing artifacts failed ws=%s run=%s: %s",
                workspace_id,
                task_run_id,
                exc.__class__.__name__,
            )
            artifacts = []
    return RunFacts(
        output_text=output_text, structured_output=structured, artifacts=tuple(artifacts)
    )


_CODE_RE = re.compile(r"[^A-Za-z0-9_.:\-]")


def _code(reason: str) -> str:
    return _CODE_RE.sub("", reason)[:_REASON_MAX]


def _summarise(results: Sequence[CriterionResult], free_text: frozenset[int] = frozenset()) -> str:
    """Tóm tắt hiển thị cho founder: CHỈ mã (id tiêu chí + mã cố định), không chứa lời giải thích tự do
    của thẩm phán (nằm riêng trong báo cáo đã lưu)."""
    ok = sum(1 for r in results if r.required and r.verdict is CriterionVerdict.PASS)
    total = sum(1 for r in results if r.required)
    tokens: list[str] = []
    for i, r in enumerate(results):
        if not r.required or r.verdict is CriterionVerdict.PASS:
            continue
        label = f"{r.id or '?'}({r.verdict.value}"
        code = "" if i in free_text else _code(r.reason)
        tokens.append(label + (f":{code}" if code else "") + ")")
    out = f"{ok}/{total} tiêu chí bắt buộc đạt"
    for token in tokens:
        if len(out) + 1 + len(token) > _SUMMARY_MAX:
            break
        out += " " + token
    return out


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def _store_report(
    plane: Any, report: VerificationReport, *, workspace_id: str, task_run_id: str
) -> VerificationReport | None:
    repo = getattr(plane, "verification_report_repository", None)
    if repo is None:
        return None
    try:
        return await repo.create_if_absent(report)
    except Exception as exc:
        logger.warning(
            "verify: storing report failed ws=%s run=%s: %s",
            workspace_id,
            task_run_id,
            exc.__class__.__name__,
        )
        return None


async def _emit_event(
    plane: Any,
    *,
    project_id: str,
    task_run_id: str,
    workspace_id: str,
    payload: dict[str, Any],
) -> None:
    try:
        await plane.run_repository.append_event(
            RunEventRecord(
                run_id=task_run_id,
                project_id=project_id,
                event_type="verification.completed",
                payload=payload,
            )
        )
    except Exception as exc:
        logger.warning(
            "verify: appending event failed ws=%s run=%s: %s",
            workspace_id,
            task_run_id,
            exc.__class__.__name__,
        )


async def verify_task_result(
    plane: Any,
    *,
    producer_spec: AgentSpec,
    workspace_id: str,
    project_id: str,
    task_id: str,
    task_run_id: str,
    task_title: str,
    decision_reason: str,
    done_criteria: dict[str, Any],
    run_result: Any,
    output_text: str,
) -> VerificationOutcome:
    """Kiểm tra kết quả task theo doneCriteria. KHÔNG BAO GIỜ ném: mọi lỗi => INCONCLUSIVE."""
    try:
        return await _verify_task_result(
            plane,
            producer_spec=producer_spec,
            workspace_id=workspace_id,
            project_id=project_id,
            task_id=task_id,
            task_run_id=task_run_id,
            task_title=task_title,
            decision_reason=decision_reason,
            done_criteria=done_criteria,
            run_result=run_result,
            output_text=output_text,
        )
    except Exception as exc:
        logger.exception(
            "verification failed ws=%s task=%s run=%s", workspace_id, task_id, task_run_id
        )
        return VerificationOutcome(
            Verdict.INCONCLUSIVE, None, f"verification_error:{exc.__class__.__name__}", []
        )


async def _verify_task_result(
    plane: Any,
    *,
    producer_spec: AgentSpec,
    workspace_id: str,
    project_id: str,
    task_id: str,
    task_run_id: str,
    task_title: str,
    decision_reason: str,
    done_criteria: dict[str, Any],
    run_result: Any,
    output_text: str,
) -> VerificationOutcome:
    try:
        parsed = parse_done_criteria(done_criteria)
    except DoneCriteriaError:
        return VerificationOutcome(Verdict.INCONCLUSIVE, None, "criteria_invalid", [])
    criteria: list[Any] = parsed["criteria"]

    facts = await collect_run_facts(
        plane,
        workspace_id=workspace_id,
        task_run_id=task_run_id,
        run_result=run_result,
        output_text=output_text,
    )

    # Tiêu chí có id hợp lệ mới được chấm; id hỏng => UNCLEAR `invalid_criterion` (fail-closed, hiển thị).
    slots: list[CriterionResult | None] = [None] * len(criteria)
    free_text: set[int] = set()  # kết quả có `reason` là lời tự do của thẩm phán (không vào note)
    rubric: list[tuple[int, dict[str, Any]]] = []
    for i, c in enumerate(criteria):
        if not _valid_id(c):
            raw = c if isinstance(c, dict) else {}
            slots[i] = CriterionResult(
                id="",
                required=bool(raw.get("required", True)),
                check="rubric" if raw.get("check") == "rubric" else "deterministic",
                verdict=CriterionVerdict.UNCLEAR,
                reason="invalid_criterion",
            )
        elif c.get("check") == "rubric":
            rubric.append((i, c))
        else:
            slots[i] = evaluate_deterministic(c, facts)

    judge: JudgeResult | None = None
    if rubric:
        judge = await run_judge(
            plane,
            producer_spec=producer_spec,
            workspace_id=workspace_id,
            project_id=project_id,
            task_run_id=task_run_id,
            task_title=task_title,
            decision_reason=decision_reason,
            rubric_criteria=[c for _, c in rubric],
            output_text=output_text,
        )
        for i, c in rubric:
            if judge.verdicts is None:
                crit_verdict, reason = CriterionVerdict.UNCLEAR, judge.error or "judge_failed"
            else:
                crit_verdict, reason = judge.verdicts.get(
                    c["id"], (CriterionVerdict.UNCLEAR, "judge_omitted")
                )
                if reason != "judge_omitted":
                    free_text.add(i)
                reason = clean_reason(reason)
            slots[i] = CriterionResult(
                id=c["id"],
                required=bool(c.get("required", True)),
                check="rubric",
                verdict=crit_verdict,
                reason=reason,
            )

    results = [r for r in slots if r is not None]
    verdict = combine(results)
    mode = "deterministic+judge" if judge is not None else "deterministic"
    summary = _summarise(results, frozenset(free_text))

    report = VerificationReport(
        report_id=f"vr_{uuid.uuid4().hex}",
        workspace_id=workspace_id,
        project_id=project_id,
        task_id=task_id,
        run_id=task_run_id,
        verifier_run_id=judge.verifier_run_id if judge is not None else None,
        verdict=verdict.value,
        mode=mode,
        criteria_results=[r.to_dict() for r in results],
        criteria_hash=_sha256(
            json.dumps(parsed, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        ),
        output_hash=_sha256(output_text),
        created_at=datetime.now(UTC),
    )
    stored = await _store_report(plane, report, workspace_id=workspace_id, task_run_id=task_run_id)
    report_id = stored.report_id if stored is not None else None
    if (
        stored is not None
        and stored.report_id != report.report_id
        and stored.verdict != verdict.value
    ):
        # Báo cáo của run này đã được lưu trước đó với kết luận khác: giữ bản đã lưu (nguồn sự thật).
        logger.warning(
            "verify: stored report verdict differs ws=%s run=%s stored=%s new=%s",
            workspace_id,
            task_run_id,
            stored.verdict,
            verdict.value,
        )
        verdict = Verdict(stored.verdict)
        mode = stored.mode
        results = [
            CriterionResult(
                id=str(d.get("id", "")),
                required=bool(d.get("required", True)),
                check=str(d.get("check", "rubric")),
                verdict=CriterionVerdict(d.get("verdict", "unclear")),
                reason=str(d.get("reason", "")),
            )
            for d in stored.criteria_results
        ]
        summary = _summarise(results, frozenset(range(len(results))))
    await _emit_event(
        plane,
        project_id=project_id,
        task_run_id=task_run_id,
        workspace_id=workspace_id,
        payload={
            "verdict": verdict.value,
            "report_id": report_id,
            "mode": mode,
            "failed": [r.id for r in results if r.verdict is CriterionVerdict.FAIL],
            "unclear": [r.id for r in results if r.verdict is CriterionVerdict.UNCLEAR],
        },
    )
    return VerificationOutcome(verdict, report_id, summary, results)
