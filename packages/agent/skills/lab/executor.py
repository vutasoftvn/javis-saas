from __future__ import annotations

from collections.abc import Callable

from agent.contracts.kernel import ExecutionKernel
from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent.evals.artifacts import EvalCaseResult, EvalRun
from agent.evals.repositories import EvalRepository
from agent.governance.contracts import PinnedSpecIdentity
from agent.skills.contracts import SkillSpec
from agent.skills.lab.models import EvalCase

__all__ = ["ScoreFn", "SkillCandidateExecutor", "default_score_fn"]

ScoreFn = Callable[[RunResult, EvalCase], float]


def default_score_fn(result: RunResult, case: EvalCase) -> float:
    """Baseline scorer: 1.0 nếu Run COMPLETED và (nếu có khai báo)
    `expected_outcome["contains"]` xuất hiện trong final_output, else 0.0.

    Đây CHỈ là fallback mặc định cho test/demo — production nên tiêm scorer
    thật (LLM-as-judge hoặc rule domain-specific) qua tham số `score_fn` của
    `SkillCandidateExecutor`, không dựa vào substring match cho đánh giá thật."""
    if result.status != RunStatus.COMPLETED:
        return 0.0
    expected_contains = case.expected_outcome.get("contains")
    if expected_contains and expected_contains not in str(result.final_output or ""):
        return 0.0
    return 1.0


class SkillCandidateExecutor:
    """Chạy 1 candidate SkillSpec qua `ExecutionKernel` thật (đường thực thi
    canonical, không phải mock riêng cho lab) với 1 bộ `EvalCase`, trả điểm
    trung bình.

    KHÔNG publish candidate vào spec registry durable — instructions của
    candidate được nối trực tiếp vào `AgentSpec.instructions` cho 1 Run tạm
    thời (`definition_hash=None` buộc tính lại hash mỗi lần, không đụng tới
    version thật của skill/agent đã publish). Tránh làm bẩn
    `agent_registry.published_specs` bằng hàng loạt version "-candidate-rN"
    throwaway.
    """

    def __init__(
        self,
        *,
        kernel: ExecutionKernel,
        base_agent_spec: AgentSpec,
        score_fn: ScoreFn = default_score_fn,
        eval_repository: EvalRepository | None = None,
    ) -> None:
        self._kernel = kernel
        self._base_agent_spec = base_agent_spec
        self._score_fn = score_fn
        self._eval_repository = eval_repository

    def _build_eval_agent_spec(self, candidate_skill: SkillSpec, run_label: str) -> AgentSpec:
        combined = self._base_agent_spec.instructions
        if candidate_skill.instructions:
            combined = f"{combined}\n\n{candidate_skill.instructions}".strip()
        # `version` phải KHÁC nhau giữa các round — publish_agent_spec() coi cùng
        # (id, version) với hash khác là conflict bất biến (đúng invariant, nhưng
        # phải tránh va vào chính nó khi nội dung candidate đổi giữa các round).
        return self._base_agent_spec.model_copy(
            update={
                "instructions": combined,
                "version": f"{self._base_agent_spec.version}-lab-{run_label}",
                "definition_hash": None,
                "pinned_skills": [],
            }
        )

    async def run_suite(
        self,
        candidate_skill: SkillSpec,
        cases: list[EvalCase],
        *,
        run_label: str,
        include_holdout: bool = True,
    ) -> tuple[float, list[float], str | None]:
        eval_agent_spec = self._build_eval_agent_spec(candidate_skill, run_label)

        eval_run_id: str | None = None
        if self._eval_repository is not None:
            target_ref = PinnedSpecIdentity(
                spec_kind="skill",
                spec_id=candidate_skill.id,
                spec_version=candidate_skill.version,
                definition_hash=candidate_skill.definition_hash or candidate_skill.compute_hash(),
            )
            created = await self._eval_repository.create_run(EvalRun(target_ref=target_ref))
            eval_run_id = created.run_id

        scores: list[float] = []
        for case in cases:
            if not include_holdout and case.is_holdout:
                continue
            req = RunRequest(
                principal="skill_optimization_lab",
                root_executable_ref=eval_agent_spec.to_pinned_identity(),
                input=case.input_payload,
            )
            result = await self._kernel.run(req, eval_agent_spec)
            score = self._score_fn(result, case)
            scores.append(score)

            if eval_run_id is not None and self._eval_repository is not None:
                await self._eval_repository.record_case_result(
                    EvalCaseResult(
                        eval_run_id=eval_run_id,
                        case_id=case.case_id,
                        passed=score >= 1.0,
                        score=score,
                    )
                )

        avg = sum(scores) / len(scores) if scores else 0.0

        if eval_run_id is not None and self._eval_repository is not None:
            await self._eval_repository.update_run_status(eval_run_id, "completed", pass_rate=avg)

        return avg, scores, eval_run_id
