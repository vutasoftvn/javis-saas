from __future__ import annotations

from typing import Callable

from agent_core.contracts.kernel import ExecutionKernel
from agent_core.contracts.run import RunRequest, RunResult, RunStatus
from agent_core.contracts.spec import AgentSpec
from agent_core.skills.contracts import SkillSpec
from agent_core.skills.lab.models import EvalCase

__all__ = ["ScoreFn", "default_score_fn", "SkillCandidateExecutor"]

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
    ) -> None:
        self._kernel = kernel
        self._base_agent_spec = base_agent_spec
        self._score_fn = score_fn

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
    ) -> tuple[float, list[float]]:
        eval_agent_spec = self._build_eval_agent_spec(candidate_skill, run_label)

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
            scores.append(self._score_fn(result, case))

        avg = sum(scores) / len(scores) if scores else 0.0
        return avg, scores
